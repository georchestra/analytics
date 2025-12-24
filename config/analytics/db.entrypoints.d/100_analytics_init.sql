CREATE SCHEMA IF NOT EXISTS analytics;
SET search_path = analytics, public;
CREATE UNLOGGED TABLE IF NOT EXISTS analytics.opentelemetry_buffer
(
    timestamp                   timestamptz,
    span_id                     text,
    trace_id                    text,
    message                     text,
    attributes                  jsonb,
    resources                   jsonb,
    scope                       jsonb,
    source_type                 text,
    severity_text               text,
    severity_number             integer,
    observed_timestamp          timestamptz,
    flags                       integer,
    dropped_attributes_count    integer
);
COMMENT ON TABLE analytics.opentelemetry_buffer IS 'Opentelemetry buffer table. Receives incoming opentelemetry logs data, for further processing and proper storage. Only contains transient data.';

CREATE TABLE IF NOT EXISTS analytics.access_logs
(
    oid                  serial,
    id                   text,
    ts                   timestamptz NOT NULL,
    message              text        NOT NULL,
    app_id               text        NOT NULL,
    app_path             text        NOT NULL,
    app_name             text        NOT NULL,
    ip                   text,
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
    client_ip            text,
    server_address       text,
    context_data         jsonb,
    PRIMARY KEY (ts, oid)
);
SELECT create_hypertable('analytics.access_logs', by_range('ts', INTERVAL '7 days'));
COMMENT ON TABLE analytics.access_logs IS 'Storage (hyper)table for the access logs processed data. This is a timescaledb-enabled table.';

CREATE UNIQUE INDEX idx_id_timestamp
  ON analytics.access_logs(ts, id);

-- Set retention policy to 3 years, see https://docs.timescale.com/api/latest/data-retention/add_retention_policy/#add_retention_policy
SELECT add_retention_policy('analytics.access_logs', drop_after => INTERVAL '3 years', schedule_interval => INTERVAL '1 week');

-- set compression
-- see https://docs.timescale.com/api/latest/compression/alter_table_compression/
--     https://docs.timescale.com/use-timescale/latest/compression/compression-policy/
ALTER TABLE access_logs SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'id'
);
SELECT add_compression_policy('access_logs', compress_after => INTERVAL '1 month');