# Configuring TimescaleDB

## TimescaleDB basic configuration

Like any PostgreSQL, there is quite a lot you can configure: number of pg_hba.conf, simultaneous connections, global tuning. Proceed for that as you would for any PostgreSQL database.
Additionnally, you might want to read:

- [Timescaledb install](https://docs.timescale.com/self-hosted/latest/install/)
- [Timescaledb config](https://docs.timescale.com/self-hosted/latest/configuration/timescaledb-config/)

## Configure for geOrchestra Analytics

For Analytics, we need some (hyper)tables to be present as well as some continuous aggregates based on them.
We provide only some aggregates, but feel free to add your own. 
About the retention policies applied on the tables, the compression etc, we can only propose some settings, but you might want to adapt them to your needs and expectations.

### Tables

#### `opentelemetry_buffer` table

This is the table that Vector will write to. It receives the Opentelemetry access log data, without any more process. 

It will be used as the source for the Python CLI when processing the access logs. 

You need at least the `opentelemetry_buffer` table to be present, so that Vector can write to it. The python CLI should be able to create it on the fly at its first run, but for now it is missing some performance optimization like having the table set as `unlogged`.

Here's a creation script for this table, to run against your database:

```sql
CREATE UNLOGGED TABLE IF NOT EXISTS analytics.opentelemetry_buffer
(
    timestamp                timestamp not null,
    span_id                  varchar   not null,
    trace_id                 varchar,
    message                  varchar   not null,
    attributes               json,
    resources                json,
    scope                    json,
    source_type              varchar,
    severity_text            varchar,
    severity_number          integer,
    observed_timestamp       timestamp,
    flags                    integer,
    dropped_attributes_count integer,
    primary key (timestamp, span_id)
);
COMMENT ON TABLE analytics.opentelemetry_buffer IS 'Opentelemetry access logs buffer table. Receives incoming access log data, for further processing and proper storage. Only contains transient data.';
```

Please note the structure. It matches with the structure of access logs provided by OpenTelemetry standard. This is the structure that the Python CLI will expect to get as input. Please don't mess with this structure.
If you need to add more data, please place them into one of the json objects, for instance `attributes` or `scope`.

#### `access_logs` table

The `analytics.access_logs` table is fed by the python CLI. For now, the CLI doesn't create it if not present, so you'll have to create it manually on the DB _before_ running the CLI for the first time.
Here the creation script:

```sql
CREATE TABLE IF NOT EXISTS analytics.access_logs
(
    oid                  serial,
    id                   text,
    ts                   timestamptz NOT NULL,
    message              text        NOT NULL,
    app_path             text        NOT NULL,
    app_name             text        NOT NULL,
    user_id              text,
    user_name            text,
    org_id               text,
    org_name             text,
    roles                text[],
    auth_method          text,
    request_method       text,
    request_path         text,
    request_query_string text,
    request_details      jsonb,
    response_time        integer,
    response_size        integer,
    status_code          integer,
    context_data         jsonb,
    PRIMARY KEY (ts, oid)
);
SELECT create_hypertable('analytics.access_logs', by_range('ts'));
COMMENT ON TABLE analytics.access_logs IS 'Storage (hyper)table for the access logs processed data. This is a timescaledb-enabled table.';
-- wcreate a unique index, see https://docs.timescale.com/use-timescale/latest/hypertables/hypertables-and-unique-indexes/
CREATE UNIQUE INDEX idx_id_timestamp
  ON analytics.access_logs(ts, id);
```

Please note that this table is a TimescaleDB _hypertable_, i.e. optimized for massive time-scaled data. To know more about this, see [hypertables](https://docs.timescale.com/use-timescale/latest/hypertables/).

`request_details` is a jsonb object, this will, as a base, contain all the request parameters. This is also where the app-specific processors of the CLI will add any interesting information it can extract (based on each app vendor-specific logic). 

!!! note "Note"

    Be mindful if adding json(b) objects inside this `request_details` jsonb object, because it might then be complicated to process when creating the continous aggregates: TimescaleDB doesn't, as of now, support sub-queries in the definition of the continuous aggregates.



## Loading the default table definitions

### On docker
For now, We haven't yet managed to load them by default on startup. You will have to load them manually once you started the docker compo:
```bash
for f in `ls -1 config/analytics/db.entrypoints.d/*.sql`; do 
  docker compose exec -T timescaledb psql -U tsdb -d analytics < $f
done
```

## Performance

Cf https://docs.timescale.com/self-hosted/latest/configuration/timescaledb-config/

### Opentelemetry_buffer table

Having the table set as `unlogged` provides a better performance, at the cost of loosing its data in case of a database crash. Since this is just analytics concern, it can be considered a reasonable compromise to ensure better performance. But feel free to remove this feature if you prefer.
