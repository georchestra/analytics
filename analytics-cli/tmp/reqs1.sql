SELECT app_path, user_name, org_name, request_details->>'service' AS service, request_details->>'request' AS request, request_details->>'layers' AS layers FROM analytics.access_logs WHERE app_name='geoserver' ;

-- Views from the old analytics
-- List of service, request, layer
SELECT count(app_path) AS nb_requests,
       request_details->>'service' AS service,
       request_details->>'request' AS request,
       request_details->>'layers' AS layers
FROM analytics.access_logs
WHERE app_name='geoserver'
GROUP BY service, request, layers;

WITH layers as (SELECT request_details->>'layers' AS js FROM analytics.access_logs WHERE oid=11603)
SELECT js,
  js IS JSON "json?",
  js IS JSON SCALAR "scalar?",
  js IS JSON OBJECT "object?",
  js IS JSON ARRAY "array?"
FROM layers;


WITH layers as (SELECT request_details->>'layers' AS js FROM analytics.access_logs WHERE oid=11603)
SELECT json_array_elements(js::json)
FROM layers;

SELECT *
FROM analytics.access_logs
CROSS JOIN LATERAL (
    SELECT
        CASE
            jsonb_array_elements_text(request_details->'layers'     )          AS layer,
             request_details->'service'          AS service,
             request_details->'request'          AS request,
             request_details->'tiled'          AS tiled,
             request_details->'yolo'          AS yolo
     WHERE oid=11603
    )
WHERE app_name='geoserver'

SELECT request_details->'layers' FROM analytics.access_logs WHERE request_details->'layers' IS JSON ARRAY

DELETE FROM analytics.access_logs WHERE request_details->'layers' IS NOT JSON ARRAY

-- Geoserver view:
SELECT id, ts, app_path, app_name, user_id, user_name, org_id, org_name, roles, request_method, request_path, response_time, response_size, status_code, layer, service, request, tiled
FROM analytics.access_logs
CROSS JOIN LATERAL (
    SELECT
            jsonb_array_elements_text(request_details->'layers') AS layer,
             request_details->'service'          AS service,
             request_details->'request'          AS request,
             request_details->'tiled'          AS tiled,
             request_details->'projection'          AS projection

     -- WHERE oid=11603
    )
WHERE app_name='geoserver'


-- Reproduce the analytics dashboard :
WITH geoserver AS (SELECT id,
                          ts,
                          app_path,
                          app_name,
                          user_id,
                          user_name,
                          org_id,
                          org_name,
                          roles,
                          request_method,
                          request_path,
                          response_time,
                          response_size,
                          status_code,
                          layer,
                          service,
                          request,
                          tiled
                   FROM analytics.access_logs
                            CROSS JOIN LATERAL (
                       SELECT jsonb_array_elements_text(request_details -> 'layers') AS layer,
                              request_details -> 'service'                           AS service,
                              request_details -> 'request'                           AS request,
                              request_details -> 'tiled'                             AS tiled,
                              request_details -> 'projection'                        AS projection

                       -- WHERE oid=11603
                       )
                   WHERE app_name = 'geoserver')
SELECT user_name, org_name, request_method, status_code, layer, service, request, tiled, count(id) as nb_req, AVG(response_time) as avg_time
FROM geoserver
GROUP BY user_name, org_name, request_method, status_code, layer, service, request, tiled;


-- Argh. Tsdb continuous aggregates don't accept sub-queries in their statement. It will make difficult exploiting the json object , specifically splitting the layers array.
-- And it needs to tap into an hypertable, not a view on an hypertable
-- I then take the decision to store the layers as a string, comma-separated. If necessary, it will be split into an array and unnested from within the Postgresql queries for dataviz


CREATE MATERIALIZED VIEW analytics.geoserver_summary_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 h', ts) AS bucket, user_name, org_name, request_method, status_code, request_details -> 'layers' AS layers,
                              request_details -> 'service'            AS service,
                              request_details -> 'request'            AS request,
                              request_details -> 'tiled'              AS tiled,
                              request_details -> 'is_download'       AS is_download,
                              request_details -> 'download_format'   AS download_format,
                              count(id)                               AS nb_req,
                              AVG(response_time)                      AS avg_time,   
                              percentile_agg(response_time::double)         AS percentile_hourly
FROM analytics.access_logs
GROUP BY bucket, user_name, org_name, request_method, status_code, request_details -> 'layers', request_details -> 'service', request_details -> 'request' , request_details -> 'tiled', request_details -> 'is_download', request_details -> 'download_format';

-- for explanations about the percentiel_agg see 
-- https://docs.timescale.com/use-timescale/latest/continuous-aggregates/hierarchical-continuous-aggregates/#roll-up-calculations



CREATE MATERIALIZED VIEW analytics.geoserver_summary_daily
WITH (timescaledb.continuous) AS
SELECT  time_bucket(INTERVAL '1 h', ts) AS bucket,
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
        nb_req,
        mean(rollup(percentile_hourly))   AS avg_time
        rollup(percentile_hourly) as percentile_daily
FROM analytics.geoserver_summary_hourly
GROUP BY bucket, user_name, org_name, request_method, status_code, layers, service, request, tiled, s_download, download_format;