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

CREATE MATERIALIZED VIEW analytics.geoserver_summary_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 day', ts) AS bucket, user_name, org_name, request_method, status_code, request_details -> 'layers' AS layers,
                              request_details -> 'service'            AS service,
                              request_details -> 'request'            AS request,
                              request_details -> 'tiled'              AS tiled,
                              request_details -> 'is_download'       AS is_download,
                              request_details -> 'download_format'   AS download_format,
                              count(id)                               AS nb_req,
                              AVG(response_time)                      AS avg_time
FROM analytics.access_logs
GROUP BY user_name, org_name, request_method, status_code, request_details -> 'layers', request_details -> 'service', request_details -> 'request' , request_details -> 'tiled', request_details -> 'is_download', request_details -> 'download_format', bucket;
-- ALTER MATERIALIZED VIEW analytics.geoserver_summary_daily set (timescaledb.materialized_only = true);
CALL refresh_continuous_aggregate('analytics.geoserver_summary_daily', '2021-05-01', '2025-05-01');

SELECT request_details->'layers' FROM analytics.access_logs WHERE request_details->'layers' IS JSON ARRAY

DELETE FROM analytics.access_logs WHERE request_details->'layers' IS NOT JSON ARRAY

CREATE VIEW analytics.geoserver_access_logs AS  (SELECT id,
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


SELECt * FROM analytics.access_logs  WHERE request_details ->> 'is_download' = 'true';



truncate analytics.access_logs;
DROP  MATERIALIZED VIEW analytics.geoserver_summary_daily;
