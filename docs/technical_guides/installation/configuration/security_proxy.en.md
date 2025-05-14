# Configuring the Security Proxy

## Configuring the Security Proxy to produce enhanced access logs

TODO: Propose an implementation of access logs with MDCs based on my wip branch

### Enabling the access logs
TODO

### Enabling enhanced access logs
TODO

### Exposing the logs over OpenTelemetry protocol

The OpenTelemetry project provides a [java-agent](https://opentelemetry.io/docs/zero-code/java/agent/) as a simple means to instrument your software.

To enable OpenTelemetry support on the Security Proxy:

- download the [OpenTelemetry javaagent](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar) and store it in the datadir's security-proxy/libs folder
- add the following _**java options**_ to enable the javaagent with all expected features:
```
-javaagent:/etc/georchestra/security-proxy/libs/opentelemetry-javaagent.jar
-Dotel.javaagent.enabled=true
-Dotel.exporter.otlp.protocol=grpc
-Dotel.exporter.otlp.endpoint=http://localhost:4317
-Dotel.instrumentation.log4j-appender.experimental.capture-mdc-attributes=*
-Dotel.traces.exporter=none
-Dotel.metrics.exporter=none
-Dotel.logs.exporter=otlp
```
Beware, those need to be declared as java JVM options, not jetty:run options.

for instance if running the Security Proxy from its source code, in commandline, this would be:
```bash
export MAVEN_OPTS="-javaagent:/etc/georchestra/security-proxy/libs/opentelemetry-javaagent.jar -Dotel.javaagent.enabled=true -Dotel.exporter.otlp.protocol=grpc -Dotel.exporter.otlp.endpoint=http://localhost:4317   -Dotel.instrumentation.log4j-appender.experimental.capture-mdc-attributes=*  -Dotel.traces.exporter=none -Dotel.metrics.exporter=none -Dotel.logs.exporter=otlp"
mvn jetty:run -Dgeorchestra.datadir=/etc/georchestra -T 2C -f security-proxy
```

You will want to adjust the `otel.exporter.otlp.endpoint` to match the Vector instance, in charge of collecting the data.
