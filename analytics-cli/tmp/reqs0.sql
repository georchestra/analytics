select * from analytics.buffer ORDER BY timestamp ASC, span_id ASC LIMIT 100 OFFSET 100

select count(*) from analytics.buffer WHERE ts < now() ORDER BY timestamp ASC, span_id ASC;

DROP TABLE analytics.access_logs;


CREATE TABLE IF NOT EXISTS analytics.access_logs
(
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
    PRIMARY KEY (ts, id)
);
SELECT create_hypertable('analytics.access_logs', by_range('ts'));
COMMENT ON TABLE analytics.access_logs IS 'Storage (hyper)table for the access logs processed data. This is a timescaledb-enabled table.';



INSERT INTO analytics.buffer (message, timestamp, attributes, resources, scope) VALUES ('coucou', now(), '{}', '{}', '{}')

select * from analytics.buffer LIMIT 1;

alter table analytics.buffer drop constraint buffer_pkey;

DELETE FROM analytics.buffer WHERE message='' OR span_id is null;

DROP TABLE analytics.access_logs;

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
-- alter table analytics.access_logs
--     add constraint u_id_timestamp
--         unique (ts, id);
-- we'll rather use this (see https://docs.timescale.com/use-timescale/latest/hypertables/hypertables-and-unique-indexes/)
CREATE UNIQUE INDEX idx_id_timestamp
  ON analytics.access_logs(ts, id);

TRUNCATE analytics.access_logs;

SELECT * from analytics.opentelemetry_buffer where message='GET 200 http://localhost:8080/geoserver/geor/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&STYLES&LAYERS=geor%3Arivers&EXCEPTIONS=application%2Fvnd.ogc.se_inimage&tiled=true&tilesOrigin=-36.969444274902344%2C-164.88743591308594&WIDTH=256&HEIGHT=256&CRS=EPSG%3A4326&BBOX=30.9375%2C78.75%2C31.640625%2C79.453125';

SELECT ts, id, count(id) FROM analytics.access_logs GROUP BY ts, id HAVING count(id) > 1 ORDER BY ts, id;

-- Deduplicate
DELETE FROM analytics.access_logs a USING analytics.access_logs b WHERE a.oid > b.oid AND a.ts = b.ts AND a.id = b.id;

