SET search_path = analytics, public;

INSERT INTO analytics.access_logs (
    id, ts, message, app_id, app_path, app_name, ip, user_id, user_name,
    org_id, org_name, roles, auth_method, request_method, request_path,
    request_query_string, request_details, response_time, response_size,
    status_code, client_ip, server_address, context_data
)
SELECT
    'fixture-' || n,
    ts,
    'Synthetic migration fixture ' || n,
    CASE WHEN n % 3 = 0 THEN '/mapstore/' ELSE '/geoserver/' END,
    CASE WHEN n % 3 = 0 THEN '/mapstore/' ELSE '/geoserver/' END,
    CASE WHEN n % 3 = 0 THEN 'mapstore' ELSE 'geoserver' END,
    '192.0.2.' || (10 + n),
    'fixture-user-id-' || (n % 4),
    CASE WHEN n % 5 = 0 THEN NULL ELSE 'fixture-user-' || (n % 4) END,
    'fixture-org-id-' || (n % 3),
    CASE WHEN n % 7 = 0 THEN NULL ELSE 'fixture-organisation-' || (n % 3) END,
    ARRAY['ROLE_USER', 'ROLE_FIXTURE'],
    'fixture-auth',
    CASE WHEN n % 4 = 0 THEN 'POST' ELSE 'GET' END,
    '/geoserver/fixture-workspace/wms',
    'service=WMS&request=GetMap&fixture=' || n,
    CASE WHEN n % 3 = 0 THEN
        jsonb_build_object('tags', jsonb_build_array('ui'), 'fixture', true)
    ELSE
        jsonb_build_object(
            'tags', jsonb_build_array('ogc'),
            'workspaces', 'fixture-workspace-' || (n % 3),
            'layers', 'fixture-layer-' || (n % 5),
            'service', CASE WHEN n % 2 = 0 THEN 'WMS' ELSE 'WFS' END,
            'request', CASE WHEN n % 2 = 0 THEN 'GetMap' ELSE 'GetFeature' END,
            'tiled', CASE WHEN n % 2 = 0 THEN 'true' ELSE 'false' END,
            'is_download', CASE WHEN n % 4 = 0 THEN 'true' ELSE 'false' END,
            'download_format', CASE WHEN n % 4 = 0 THEN 'application/json' ELSE NULL END,
            'user_agent_family', 'fixture-client',
            'referrer', 'https://example.test/fixture'
        )
    END,
    10 + n,
    1000 + n,
    CASE WHEN n % 11 = 0 THEN 500 ELSE 200 END,
    '198.51.100.' || (10 + n),
    'analytics.example.test',
    jsonb_build_object('fixture', true)
FROM (
    VALUES
        (1,  '2026-01-31 22:30+00'::timestamptz),
        (2,  '2026-01-31 23:30+00'::timestamptz),
        (3,  '2026-02-01 00:30+00'::timestamptz),
        (4,  '2026-03-29 00:30+00'::timestamptz),
        (5,  '2026-03-29 01:15+00'::timestamptz),
        (6,  '2026-03-29 02:30+00'::timestamptz),
        (7,  '2026-04-30 22:30+00'::timestamptz),
        (8,  '2026-04-30 23:30+00'::timestamptz),
        (9,  '2026-05-01 00:30+00'::timestamptz),
        (10, '2026-10-25 00:30+00'::timestamptz),
        (11, '2026-10-25 01:30+00'::timestamptz),
        (12, '2026-10-25 02:30+00'::timestamptz),
        (13, '2026-11-01 00:30+00'::timestamptz),
        (14, '2026-11-01 01:30+00'::timestamptz),
        (15, '2026-11-02 12:00+00'::timestamptz),
        (16, '2026-11-03 12:00+00'::timestamptz)
) AS fixture(n, ts);

INSERT INTO analytics.opentelemetry_buffer (
    timestamp, span_id, trace_id, message, attributes, resources, scope,
    source_type, severity_text, severity_number, observed_timestamp, flags,
    dropped_attributes_count
) VALUES (
    '2026-11-03 13:00+00', 'fixture-span', 'fixture-trace',
    'Synthetic OpenTelemetry fixture', '{"fixture":true}', '{"fixture":true}',
    '{"name":"fixture"}', 'fixture', 'INFO', 9,
    '2026-11-03 13:00:01+00', 0, 0
);

CALL refresh_continuous_aggregate(
    'analytics.ogc_summary_hourly', '2026-01-01', '2026-12-01');
CALL refresh_continuous_aggregate(
    'analytics.ogc_summary_daily', '2026-01-01', '2026-12-01');
CALL refresh_continuous_aggregate(
    'analytics.ogc_summary_monthly', '2026-01-01', '2026-12-01');

SELECT compress_chunk(chunk, if_not_compressed => true)
FROM show_chunks('analytics.access_logs') AS chunk
ORDER BY chunk::text
LIMIT 1;
