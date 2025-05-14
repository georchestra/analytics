# Prerequisites

## Hardware

It shouldn't be too hungry in CPU or RAM resources. But you should expect the collected logs data to take a fair amount of space.
This will of course depend on your platform's usage and how you configure the retention/aggregation in the TimescaleDB storage, but you should expect the database to use several tens of Gigabytes of disk space per year.

TODO: be more specific

## Software

### Apache Superset

Analytics vizualizations rely on Apache Superset. geOrchestra provides you the means to deploy a customized Superset instance that will integrate well into geOrchestra.

See [georchestra-superset](https://docs.georchestra.org/superset/en/latest/) on how to install and configure it.

Since analytics' components are loosely coupled, you are free to choose another dashboarding solution for your vizualizations. But you will have to configure your dashboard yourself.

### Security proxy / Gateway / reverse proxy

For now, the analytics data is collected from the access logs provided by your entrypoint. It's better to collect them at the Security proxy / Gateway level since you will get the user profile. But you can also tap into your reverse proxy's access logs (nginx, apache httpd, traefik, etc).

You can even do with a combination of them, but _take care to avoid duplicates_ (can be handled at Vector level to some extent).

#### Gateway version

##### Gateway >= 2.0.0
Starting at version 2.0.0, the Gateway is fully able to generate access logs with an advanced logging mechanism (see https://www.georchestra.org/georchestra-gateway/user_guide/configuration/#access-logging).

It is only missing `response_time` and `response_size` attributes.  
The access log message is also a bit simple.

##### Gateway < 2.0.0
Gateway versions 1.x will support OpenTelemetry but don't provide such access logs. It is still possible though to enable Netty access logs with the JVM argument  
`-Dreactor.netty.http.server.accessLogEnabled=true`.  
Combined with enabling Opentelemetry support as documented in [Gateway configuration](configuration/gateway.md), you can get Opentelemetry logs with no MDCs but with a good-enough access log message. Which can be processed by the CLI if you enable in the config:
```yaml
   opentelemetry:
    text_message_parser:
      enable: true
```
and set the proper regular expression.

You will not get the user-related information though.

#### Security Proxy

Access logs generation is not yet provided. There is a POC somewhere, so the support will be coming soon.


### Python

Part of the processing of the access logs is done using a python script. It will require a working python (virtual) environment. Of course, if running a containerized environment, it will take care of this for you.

TODO: add python minimal version
