DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;
CREATE TABLE analytics.logs
(
    time   timestamp with time zone NOT NULL,
    username      TEXT,
    org           TEXT,
    roles         TEXT,
    request_path  TEXT,
    request_type  TEXT,
    user_agent    TEXT,
    app_name      TEXT,
    app_details   json,
    response_time TEXT,
    response_size TEXT,
    http_code     TEXT
);

SELECT create_hypertable('analytics.logs', by_range('time'));
CREATE INDEX idx_username_time ON analytics.logs (username, time DESC);
CREATE INDEX idx_org_time ON analytics.logs (org, time DESC);
CREATE INDEX idx_app_time ON analytics.logs (app_name, time DESC);

-- reproduce the OGC analytics view (daily instead of monthly because my sample data doesn't cover a month
CREATE MATERIALIZED VIEW analytics.logs_geoserver_ogc_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 day', time) AS bucket,
   app_details->>'service' AS ogc_service,
   app_details->>'layers' AS ogc_layer,
   app_details->>'request' AS ogc_request,
   count(*)
FROM analytics.logs
WHERE app_name='geoserver'
GROUP BY bucket, app_details->>'service', app_details->>'layers', app_details->>'request'
ORDER BY bucket, ogc_layer, ogc_service, ogc_request;

