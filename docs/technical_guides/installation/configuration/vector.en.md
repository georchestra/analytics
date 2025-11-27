# Configuring Vector

[Vector](https://vector.dev/docs) is the piece of software in charge or collecting the logs exposed with the OpenTelemetry standard and shipping them to the database.
It is a kind of ETL specialized with observability data (logs, traces, metrics), actually not limited at all to OpenTelemetry standard.

It is a server application, listening on ports 4317 (gRPC) and 4318 (http protobuff) for observability data sent by other applications.

Between `source` (input) and `sink` (output), it can apply transformations and filters. It can even merge some log records that would share some common identifier like the span_id. 

When pushing access log data into the database buffer table, it is expected that you maintain the data structure used by opentelemetry. The target table is by default configured to be called `analytics.opentelemetry_buffer` (`analytics` is the schema).

It is all configured in a single yaml configuration file. Here's a sample, simple config:

_vector.yml:_
```yaml
api:
  enabled: true
  address: 0.0.0.0:8686
sources:
  opentelemetry:
    type: opentelemetry
    grpc:
      address: 0.0.0.0:4317
    http:
      address: 0.0.0.0:4318
      headers: []
      keepalive:
        max_connection_age_jitter_factor: 0.1
        max_connection_age_secs: 300
transforms:
  access_logs_filter:
    # Accept only access logs
    type: filter
    inputs:
      - opentelemetry.logs
    condition:
      type: "vrl"
      # source: '.scope.name == "org.georchestra.*.accesslog" || .scope.name == "org.georchestra.gateway.accesslog" '
      source: match!(.scope.name, r'org.georchestra.*.accesslog')

sinks:
#  console:
#    type: console
#    # https://vector.dev/docs/reference/configuration/sinks/console/
#    inputs:
#      - access_logs_filter
#      # - opentelemetry.logs
#    target: stdout
#    encoding:
#      codec: json
  database:
    type: postgres
    # https://vector.dev/docs/reference/configuration/sinks/postgres/
    inputs:
      - access_logs_filter
    endpoint: postgres://tsdb:password@timescaledb/analytics
    table: analytics.opentelemetry_buffer
    pool_size: 10
```

!!! tip "Tip"

    If you uncomment the console sink, you will also get the output on stdout, which is very practical when debugging 
    the workflow. You can also choose to log on stdout the opentelemetry.logs raw data instead of the data filtered 
    by Vector.

To know more about Vector configuration, please read its documentation on [https://vector.dev/docs](https://vector.dev/docs).

