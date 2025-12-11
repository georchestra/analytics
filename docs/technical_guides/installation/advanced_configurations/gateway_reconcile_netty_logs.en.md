# Reconcile Netty Logs and Gateway Opentelemetry logs

The Gateway is based on Spring Cloud Gateway project, and uses Netty server as its http server.
Netty can be configured to generate access logs. It is quite easy.

For analytics purpose, we recommend to use the Gateway Opentelemetry exporter and skip Netty's logs.

However, at the time of writing this documentation, the Gateway telemetry exporter misses some interesting metrics, for
instance the response size.
While Netty does provide it.

This page show you how you might merge logs data from both Netty and Gateway. This is kind of a hack and possibly not
good for performance. _This is to be considered experimental stuff_.

## How can we do this ?

If you followed this documentation, Vector already gets the logs for the Gateway through the Gateway Opentelemetry
exporter.

We will turn on access logs for Netty. They will be sent to Vector too.

Vector provides a service called `reduce` that can merge logs that have an identical identifier (the `span_id` here).
This service is what will merge the logs. The output from Vector will look like before, but enriched with some more
information.

![workflow](../../../d2/reconcile_netty_gateway.svg)

## Procedure

### Configure Netty to generate access logs

This is the simple part. When running the Gateway, just add the following JAVA option:

```
-Dreactor.netty.http.server.accessLogEnabled=true 
```

And restart the Gateway. If it was already sending the Gateway access logs to Vector, you will see the Netty logs too
passing by.

### Configure Vector to merge logs

Vector can take several inputs. And possibly merge them. We just need to rely on a bit more complex configuration file
for Vector. In a nutshell, it will:

- add a transform of type `filter`, to select the Netty logs
- clean up (`remap` transform) both Netty and Gateway logs, in order to remove possible redundancy (Vector will not
  accept conflicts on an attribute)
- combine the log entries into a single one, using the `reduce` transform.
- set this combined filter as the input for the DB "sink"

#### Netty filter

```yaml
transforms:
  ...
  netty_logs_filter:
    # Accept only access logs
    type: filter
    inputs:
      - opentelemetry.logs
    condition:
      type: "vrl"
      source: .scope.name == "reactor.netty.http.server.AccessLog"
```

#### Clean up both logs

This example will just take the CLF-like message from Netty and drop the rest. More complicated setups might be
considered.

```yaml
transforms:
  ...
  netty_log_pre_reduce:
    # Drop any fields that we won't be interested in when merging with accesslogs
    type: "remap"
    inputs:
      - netty_logs_filter
    source: |
      del(.attributes)
      del(.dropped_attributes_count)
      del(.flags)
      del(.observed_timestamp)
      del(.resources)
      del(.severity_number)
      del(.severity_text)
      del(.source_type)
      del(.timestamp)
      del(.trace_id)

  gateway_log_pre_reduce:
    # Drop any fields that we won't be interested in when merging with accesslogs
    type: "remap"
    inputs:
      - gw_access_logs_filter
    source: |
      del(.message)
```

### Combine the log entries

```yaml
transforms:
  ...
  gw_log_reduce:
    # Combine GW access logs and matching netty accesslogs
    type: reduce
    inputs:
      - netty_log_pre_reduce
      - gateway_log_pre_reduce
    expire_after_ms: 500
    flush_period_ms: 100
    group_by:
      - span_id
    merge_strategies:
      message: concat_newline
      scope.name: concat
```

#### Set it as input for the DB sink

```yaml

sinks:
  tsdb:
    type: postgres
    # https://vector.dev/docs/reference/configuration/sinks/postgres/
    inputs:
      - gw_log_reduce
    endpoint: "postgres://${TSDB_USER}:${TSDB_PASSWORD}@${TSDB_HOST}:${TSDB_PORT}/${TSDB_NAME}"
    table: "${TSDB_OTEL_TABLE:-analytics.opentelemetry_buffer}"
    pool_size: 5
```

Full config file can be found here: [vector.yaml](./netty_gw_reconcile_vector_config.yml)