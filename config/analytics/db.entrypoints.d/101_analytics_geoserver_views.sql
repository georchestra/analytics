SET search_path = analytics, public;

CREATE MATERIALIZED VIEW analytics.geoserver_summary_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 h', ts, 'Europe/Paris') AS bucket_hourly, user_name, org_name, request_method,  status_code,
    request_details ->> 'layers' AS layers,
    request_details ->> 'service'            AS service,
    request_details ->> 'request'            AS request,
    request_details ->> 'tiled'              AS tiled,
    request_details ->> 'is_download'       AS is_download,
    request_details ->> 'download_format'   AS download_format,
    request_details ->> 'user_agent_family' AS user_agent_family,
    count(id)                               AS nb_req,
    AVG(response_time)                      AS avg_time,
    percentile_agg(response_time::DOUBLE PRECISION)         AS percentile_hourly
FROM analytics.access_logs
GROUP BY bucket_hourly, user_name, org_name, request_method, status_code, request_details ->> 'layers',
    request_details ->> 'service', request_details ->> 'request' , request_details ->> 'tiled',
    request_details ->> 'is_download', request_details ->> 'download_format', request_details ->> 'user_agent_family';

-- for explanations about the percentile_agg see
-- https://docs.timescale.com/use-timescale/latest/continuous-aggregates/hierarchical-continuous-aggregates/#roll-up-calculations


SELECT add_retention_policy('analytics.geoserver_summary_hourly', drop_after => INTERVAL '3 weeks', schedule_interval => INTERVAL '1 day');

-- set compression
-- see https://docs.timescale.com/use-timescale/latest/continuous-aggregates/compression-on-continuous-aggregates/
SELECT add_continuous_aggregate_policy('analytics.geoserver_summary_hourly',
  initial_start => '2025-11-11 00:00:05',
  start_offset => INTERVAL '3 days',
  schedule_interval => INTERVAL '1 hour');
ALTER MATERIALIZED VIEW analytics.geoserver_summary_hourly set (timescaledb.compress = true);
SELECT add_compression_policy('analytics.geoserver_summary_hourly', compress_after=>'4 days'::interval);


CREATE MATERIALIZED VIEW analytics.geoserver_summary_daily
WITH (timescaledb.continuous) AS
SELECT  time_bucket(INTERVAL '1 d', bucket_hourly, 'Europe/Paris') AS bucket_daily,
        user_name,
        org_name,
        request_method,
        status_code,
        layers,
        service,
        request,
        tiled,
        is_download,
        download_format,
        user_agent_family,
        SUM(nb_req)                               AS nb_req,
        mean(rollup(percentile_hourly))   AS avg_time,
        rollup(percentile_hourly) as percentile_daily
FROM analytics.geoserver_summary_hourly
GROUP BY bucket_daily, user_name, org_name, request_method, status_code, layers, service, request, tiled, is_download,
         download_format, user_agent_family;

SELECT add_retention_policy('analytics.geoserver_summary_daily', drop_after => INTERVAL '2 years', schedule_interval => INTERVAL '1 week');

-- set compression
-- see https://docs.timescale.com/use-timescale/latest/continuous-aggregates/compression-on-continuous-aggregates/
SELECT add_continuous_aggregate_policy('analytics.geoserver_summary_daily',
  initial_start => '2025-11-11 00:00:05',
  start_offset => INTERVAL '3 weeks',
  end_offset => INTERVAL '1 d',
  schedule_interval => INTERVAL '1 d');
ALTER MATERIALIZED VIEW analytics.geoserver_summary_daily set (timescaledb.compress = true);
SELECT add_compression_policy('analytics.geoserver_summary_daily', compress_after=>'4 weeks'::interval);



CREATE MATERIALIZED VIEW analytics.geoserver_summary_monthly
WITH (timescaledb.continuous) AS
SELECT  time_bucket(INTERVAL '1 month', bucket_daily, 'Europe/Paris') AS bucket_monthly,
        user_name,
        org_name,
        request_method,
        status_code,
        layers,
        service,
        request,
        tiled,
        is_download,
        download_format,
        user_agent_family,
        SUM(nb_req)                               AS nb_req,
        mean(rollup(percentile_daily))   AS avg_time,
        rollup(percentile_daily) as percentile_monthly
FROM analytics.geoserver_summary_daily
GROUP BY bucket_monthly, user_name, org_name, request_method, status_code, layers, service, request, tiled, is_download,
         download_format, user_agent_family;

-- set compression
-- see https://docs.timescale.com/use-timescale/latest/continuous-aggregates/compression-on-continuous-aggregates/
SELECT add_continuous_aggregate_policy('analytics.geoserver_summary_monthly',
  initial_start => '2025-11-11 00:00:05',
  start_offset => INTERVAL '6 months',
  end_offset => INTERVAL '1 week',
  schedule_interval => INTERVAL '1 week');
ALTER MATERIALIZED VIEW analytics.geoserver_summary_monthly set (timescaledb.compress = true);
SELECT add_compression_policy('analytics.geoserver_summary_monthly', compress_after=>'7 months'::interval);


CALL refresh_continuous_aggregate('analytics.geoserver_summary_hourly', '2021-05-01', '2025-05-14');
CALL refresh_continuous_aggregate('analytics.geoserver_summary_daily', '2021-05-01', '2025-05-14');
CALL refresh_continuous_aggregate('analytics.geoserver_summary_monthly', '2021-05-01', '2025-05-14');


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


