# Configuring the Gateway

## Configuring the Gateway to produce enhanced access logs

The Gateway provides sophisticated logging capacity, extensively
covered [in its own doc](https://docs.georchestra.org/gateway/en/latest/user_guide/logging/).

We will only cover the parts relevant to the needs of this module, but reading the dedicated doc is strongly advised for
a better understanding.

### Enabling the access logs

As stated
in [Gateway#access-logging](https://docs.georchestra.org/gateway/en/latest/user_guide/logging/#access-logging), you can
enable the access logs in the datadir's gateway/logging.yaml file with:

```yaml
logging:
  accesslog:
    enabled: true
    # URLs to log at INFO level
    info:
      - ".*/(ows|ogc|wms|wfs|wcs|wps)(/.*|\?.*)?$"
```

With the above configuration, the access logs will be enabled and will only ouput on `info` level (the default) the
paths matching the regular expression.
Regular expression filtering of the access logs is useful to avoid bloating the pipeline with undesired content.

!!! note "Note"

    You will want to add more patterns to collect more data.

!!! tip "Tip"

    You don't need to activate the json-logs pattern. OpenTelemetry log collect is not tied to this setting, so you
    can keep text logs on the console while retrieving json-structured logs through opentelemetry export.

### Enabling enhanced access logs

It is possible to attach more information to the access logs, like for instance user name, roles, organization and more
detailed information about the http requests.
This is done through configuration, in the datadir's `gateway/logging.yaml` file, as documented
in [Gateway#MDC Properties](https://docs.georchestra.org/gateway/en/latest/user_guide/logging/#mdc-properties).

For usage data collection, you will at least want to enable :

```yaml

# User authentication MDC properties
user:
  id: true
  roles: true
  org: true
  auth-method: true
http:
  id: true
  method: true
  url: true
  query-string: true
  parameters: true
  headers: true
  headers-pattern: "(?i)user-agent"

```

### Exposing the logs over OpenTelemetry protocol

The OpenTelemetry project provides a [java-agent](https://opentelemetry.io/docs/zero-code/java/agent/) as a simple means
to instrument your software.

To enable OpenTelemetry support on the Gateway:

- download
  the [OpenTelemetry javaagent](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar)
  and store it in the datadir's gateway/libs folder
- add the following _**java options**_ to enable the javaagent with all expected features:

```
-javaagent:/etc/georchestra/gateway/libs/opentelemetry-javaagent.jar
-Dotel.javaagent.enabled=true
-Dotel.exporter.otlp.protocol=grpc
-Dotel.exporter.otlp.endpoint=http://localhost:4317
-Dotel.instrumentation.logback-appender.experimental.capture-mdc-attributes=*
-Dotel.traces.exporter=none
-Dotel.metrics.exporter=none
-Dotel.logs.exporter=otlp
```

!!! warning "Warning"

    Beware, those need to be declared as java JVM options, not spring-boot options.

For instance if running the gateway from its source code, in commandline, this would be:

```bash
otel_endpoint=http://localhost:4317

./mvnw -DskipTests spring-boot:run \
    -Dspring-boot.run.profiles=dev \
    -Dspring-boot.run.jvmArguments="
        -javaagent:/etc/georchestra/gateway/libs/opentelemetry-javaagent.jar \
        -Dotel.javaagent.enabled=true \
        -Dotel.exporter.otlp.protocol=grpc \
        -Dotel.exporter.otlp.endpoint=${otel_endpoint}   \
        -Dotel.instrumentation.logback-appender.experimental.capture-mdc-attributes=*  \
        -Dotel.traces.exporter=none \
        -Dotel.metrics.exporter=none \
        -Dotel.logs.exporter=otlp \
    "   \
    -pl :georchestra-gateway
```

_You will want to adjust the `otel_endpoint` variable to match the Vector instance, in charge of collecting the data._

TODO: provide the environment variable equivalent

!!! note "Some contextual information about logging and the Gateway"

    You might see another way to retrieve access logs. By default, Spring Cloud Gateway reactive, on which the 
    geOrchestra Gateway is built, uses Netty as its internal webserver. 
    Netty can be configured to enable its access logs. But this is not how we manage it in the gateway and, regarding 
    analytics purposes, even though you can use them, you will get poor and less consistent results (no user/org info 
    noticeably)

!!! tip "json-logs"

    You will read on the Gateway's documentation instructions on how to enable JSON log format. And since the 
    user/roles/org information is only visible with the JSON output, you might think that it is necessary for the 
    collection of all interesting information, for analytics purposes.  
    ***It is not***.   
    Those are two separate concerns:

    - json-logs will affect the logs sent to the logs handlers, most commonly the console (or file output). It's up
      to you to decide if you prefer CLF-like text logs lines, or json records for this.
    - the logs collected using OpenTelemetry will be sent in JSON structure *anyway*, including all MDCs, including 
      user/roles/org information. Provided you follow the 
      [related config instructions](https://docs.georchestra.org/gateway/en/latest/user_guide/configuration/#userauthentication-mdc-properties), 
      of course.



