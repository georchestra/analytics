DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;
CREATE TABLE analytics.logs
(
    timestamptz   timestamp with time zone,
    username          VARCHAR(100),
    org           VARCHAR(100),
    roles         VARCHAR(100),
    request_path           VARCHAR(500),
    request_type VARCHAR(10),
    user_agent    VARCHAR(100),
    app_name      VARCHAR(100),
    app_details   json,
    response_time VARCHAR(100),
    response_size VARCHAR(100),
    http_code     VARCHAR(100)
);