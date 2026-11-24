#!/bin/sh

set -eu
. "$(dirname -- "$0")/lib.sh"

require_command docker
require_command "$CLI"

name="analytics-migration-fresh"
volume="analytics-migration-fresh-data"

cleanup() {
    remove_container "$name"
    remove_volume "$volume"
}
trap cleanup EXIT INT TERM

cleanup
docker volume create "$volume" >/dev/null
start_database "$name" "$volume" "timescale/timescaledb:2.30.2-pg18"
run_cli db upgrade

state=$(psql_in "$name" -Atc "
    SELECT
        (SELECT version_num FROM analytics.alembic_version) || '|' ||
        (SELECT count(*) FROM timescaledb_information.hypertables
         WHERE hypertable_schema = 'analytics' AND hypertable_name = 'access_logs') || '|' ||
        (SELECT count(*) FROM information_schema.views
         WHERE table_schema = 'analytics'
           AND table_name IN ('ogc_summary_hourly', 'ogc_summary_daily', 'ogc_summary_monthly'));
")
[ "$state" = "0003|1|3" ] || {
    echo "Unexpected fresh database state: $state" >&2
    exit 1
}

# During the Europe/Paris autumn transition, the repeated local hour maps to
# two distinct timestamptz buckets and both remain inside the SQL prefilter.
dst_fallback=$(psql_in "$name" -Atc "
    WITH samples(ts) AS (
        VALUES
            ('2026-10-25 00:30:00+00'::timestamptz),
            ('2026-10-25 01:30:00+00'::timestamptz)
    ), bucketed AS (
        SELECT
            ts,
            time_bucket(INTERVAL '1 hour', ts, 'Europe/Paris') AS bucket
        FROM samples
    )
    SELECT count(DISTINCT bucket) || '|' || bool_and(ts >= bucket)
    FROM bucketed;
")
[ "$dst_fallback" = "2|true" ] || {
    echo "Unexpected Europe/Paris DST fallback bucketing: $dst_fallback" >&2
    exit 1
}

# Exercise the production aggregation query as well as time_bucket itself.
# 02:30 occurs twice locally, but each occurrence must survive in its UTC bucket.
psql_in "$name" -c "
    INSERT INTO analytics.access_logs (
        id, ts, message, app_id, app_path, app_name, request_method,
        request_details, response_time, status_code, server_address
    ) VALUES
        (
            'dst-first', '2026-10-25 00:30:00+00', 'DST fallback first hour',
            'geoserver', '/geoserver', 'GeoServer', 'GET',
            '{\"tags\":[\"ogc\"],\"service\":\"WMS\",\"request\":\"GetMap\"}',
            100, 200, 'analytics.example.test'
        ),
        (
            'dst-second', '2026-10-25 01:30:00+00', 'DST fallback second hour',
            'geoserver', '/geoserver', 'GeoServer', 'GET',
            '{\"tags\":[\"ogc\"],\"service\":\"WMS\",\"request\":\"GetMap\"}',
            200, 200, 'analytics.example.test'
        );
    INSERT INTO analytics.ogc_aggregation_queue (bucket_hourly)
    SELECT DISTINCT time_bucket(INTERVAL '1 hour', ts, 'Europe/Paris')
    FROM analytics.access_logs
    WHERE id IN ('dst-first', 'dst-second');
" >/dev/null
run_cli aggregate-ogc

dst_aggregated=$(psql_in "$name" -Atc "
    SELECT
        (SELECT count(DISTINCT bucket_hourly)
         FROM analytics.ogc_summary_hourly
         WHERE bucket_hourly >= '2026-10-25 00:00:00+00'
           AND bucket_hourly < '2026-10-25 02:00:00+00') || '|' ||
        (SELECT sum(nb_req)
         FROM analytics.ogc_summary_hourly
         WHERE bucket_hourly >= '2026-10-25 00:00:00+00'
           AND bucket_hourly < '2026-10-25 02:00:00+00');
")
[ "$dst_aggregated" = "2|2" ] || {
    echo "DST fallback requests were lost during aggregation: $dst_aggregated" >&2
    exit 1
}

echo "Fresh database upgrade to Alembic head OK."
