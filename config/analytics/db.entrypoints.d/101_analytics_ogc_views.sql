SET search_path = analytics, public;

CREATE MATERIALIZED VIEW analytics.ogc_summary_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 h', ts, 'Europe/Paris') AS bucket_hourly,
    app_id,
    app_name,
    user_name,
    org_name,
    request_method,
    status_code,
    server_address,
    request_details ->> 'workspaces' AS workspaces,
    request_details ->> 'layers' AS layers,
    request_details ->> 'service'            AS service,
    request_details ->> 'request'            AS request,
    request_details ->> 'tiled'              AS tiled,
    request_details ->> 'is_download'       AS is_download,
    request_details ->> 'download_format'   AS download_format,
    request_details ->> 'user_agent_family' AS user_agent_family,
    request_details ->> 'referrer' AS referrer,
    count(id)                               AS nb_req,
    percentile_cont(0.5) WITHIN GROUP (
        ORDER BY
            response_time::DOUBLE PRECISION
    ) AS response_time_median,
    min(response_time::DOUBLE PRECISION) AS response_time_min,
    max(response_time::DOUBLE PRECISION) AS response_time_max
FROM analytics.access_logs
WHERE request_details ->'tags' @> '["ogc"]'
GROUP BY bucket_hourly, app_id, app_name, user_name, org_name, request_method, status_code, server_address,
    request_details ->> 'workspaces', request_details ->> 'layers', request_details ->> 'service',
    request_details ->> 'request' , request_details ->> 'tiled', request_details ->> 'is_download',
    request_details ->> 'download_format', request_details ->> 'user_agent_family', request_details ->> 'referrer';

-- median would be better estimated using percentiel_agg
-- https://docs.timescale.com/use-timescale/latest/continuous-aggregates/hierarchical-continuous-aggregates/#roll-up-calculations
-- but it belongs to timescaledb_toolkit, which is a heavier dependency.


SELECT add_retention_policy('analytics.ogc_summary_hourly', drop_after => INTERVAL '3 weeks', schedule_interval => INTERVAL '1 day');

-- The date below serves to anchor the 1h interval to a given moment (in this case, every hour past 5 min 5 second).
-- If not declared, it would anchor the the moment the script was run, meaning any time possible, which we don't want.
SELECT add_continuous_aggregate_policy('analytics.ogc_summary_hourly',
  initial_start => '2025-11-11 00:05:05',
  start_offset => INTERVAL '7 days',
  end_offset => INTERVAL '0 hours',
  schedule_interval => INTERVAL '1 hour');


CREATE MATERIALIZED VIEW analytics.ogc_summary_daily
WITH (timescaledb.continuous) AS
SELECT  time_bucket(INTERVAL '1 d', bucket_hourly, 'Europe/Paris') AS bucket_daily,
    app_id,
    app_name,
    user_name,
    org_name,
    request_method,
    status_code,
    server_address,
    workspaces,
    layers,
    service,
    request,
    tiled,
    is_download,
    download_format,
    user_agent_family,
    referrer,
    SUM(nb_req)                       AS nb_req,
    percentile_cont(0.5) WITHIN GROUP (
        ORDER BY
            response_time_median
    ) AS response_time_median,
    min(response_time_min) AS response_time_min,
    max(response_time_max) AS response_time_max
FROM analytics.ogc_summary_hourly
GROUP BY bucket_daily, app_id, app_name, user_name, org_name, request_method, status_code, server_address, workspaces,
     layers, service, request, tiled, is_download, download_format, user_agent_family, referrer;

SELECT add_retention_policy('analytics.ogc_summary_daily', drop_after => INTERVAL '2 years', schedule_interval => INTERVAL '1 week');

SELECT add_continuous_aggregate_policy('analytics.ogc_summary_daily',
  initial_start => '2025-11-11 00:00:05',
  start_offset => INTERVAL '3 weeks',
  end_offset => INTERVAL '0 hours',
  schedule_interval => INTERVAL '1 d');



CREATE MATERIALIZED VIEW analytics.ogc_summary_monthly
WITH (timescaledb.continuous) AS
SELECT  time_bucket(INTERVAL '1 month', bucket_daily, 'Europe/Paris') AS bucket_monthly,
    app_id,
    app_name,
    user_name,
    org_name,
    request_method,
    status_code,
    server_address,
    workspaces,
    layers,
    service,
    request,
    tiled,
    is_download,
    download_format,
    user_agent_family,
    referrer,
    SUM(nb_req)                      AS nb_req,
    percentile_cont(0.5) WITHIN GROUP (
        ORDER BY
            response_time_median
    ) AS response_time_median,
    min(response_time_min) AS response_time_min,
    max(response_time_max) AS response_time_max
FROM analytics.ogc_summary_daily
GROUP BY bucket_monthly, app_id, app_name, user_name, org_name, request_method, status_code, server_address, workspaces,
     layers, service, request, tiled, is_download, download_format, user_agent_family, referrer;

SELECT add_continuous_aggregate_policy('analytics.ogc_summary_monthly',
  initial_start => '2025-11-11 00:00:05',
  start_offset => INTERVAL '6 months',
  end_offset => INTERVAL '0 hours',
  schedule_interval => INTERVAL '1 month');


CALL refresh_continuous_aggregate('analytics.ogc_summary_hourly', '2021-05-01', '2026-05-14');
CALL refresh_continuous_aggregate('analytics.ogc_summary_daily', '2021-05-01', '2026-05-14');
CALL refresh_continuous_aggregate('analytics.ogc_summary_monthly', '2021-05-01', '2026-05-14');

-- Watch retention policies state (see https://docs.timescale.com/api/latest/data-retention/add_retention_policy/#add_retention_policy):
-- SELECT j.hypertable_name,
--        j.job_id,
--        config,
--        schedule_interval,
--        job_status,
--        last_run_status,
--        last_run_started_at,
--        js.next_start,
--        total_runs,
--        total_successes,
--        total_failures
--   FROM timescaledb_information.jobs j
--   JOIN timescaledb_information.job_stats js
--     ON j.job_id = js.job_id
--   WHERE j.proc_name = 'policy_retention';
