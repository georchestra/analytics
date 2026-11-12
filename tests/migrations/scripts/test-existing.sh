#!/bin/sh

set -eu
. "$(dirname -- "$0")/lib.sh"

require_command docker
require_command "$CLI"

source_version=${1:-2.30.2}
target_version=2.30.2
fixture="$TEST_ROOT/fixtures/dumps/existing-timescaledb-${source_version}.dump"
name="analytics-migration-existing"
volume="analytics-migration-existing-data"

cleanup() {
    remove_container "$name"
    remove_volume "$volume"
}
trap cleanup EXIT INT TERM

test -r "$fixture" || {
    echo "Missing fixture: $fixture. Run make migration-fixtures." >&2
    exit 1
}

cleanup
docker volume create "$volume" >/dev/null
start_database "$name" "$volume" "timescale/timescaledb:${source_version}-pg18"
psql_in "$name" -c "SELECT timescaledb_pre_restore();"
docker cp "$fixture" "$name:/tmp/fixture.dump"
docker exec "$name" pg_restore -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-privileges --exit-on-error /tmp/fixture.dump
psql_in "$name" -c "SELECT timescaledb_post_restore();"

unsafe=$(psql_in "$name" -Atc "
    SELECT count(*)
    FROM analytics.access_logs
    WHERE message NOT LIKE 'Synthetic migration fixture %'
       OR ip NOT LIKE '192.0.2.%'
       OR client_ip NOT LIKE '198.51.100.%'
       OR server_address <> 'analytics.example.test'
       OR request_query_string NOT LIKE '%fixture=%'
       OR COALESCE(user_name, 'fixture-user-null') NOT LIKE 'fixture-user-%'
       OR COALESCE(org_name, 'fixture-organisation-null') NOT LIKE 'fixture-organisation-%'
       OR context_data <> '{\"fixture\": true}'::jsonb;
")
[ "$unsafe" = "0" ] || {
    echo "Fixture anonymity validation failed: $unsafe unsafe rows" >&2
    exit 1
}

before=$(psql_in "$name" -Atc "SELECT count(*) || '|' || min(ts) || '|' || max(ts) FROM analytics.access_logs;")

if [ "$source_version" != "$target_version" ]; then
    docker stop "$name" >/dev/null
    docker rm "$name" >/dev/null
    start_database "$name" "$volume" "timescale/timescaledb:${target_version}-pg18"
    psql_in "$name" -c "ALTER EXTENSION timescaledb UPDATE;"
fi

installed=$(psql_in "$name" -Atc "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';")
[ "$installed" = "$target_version" ]

run_cli db bootstrap-existing --revision 0001
run_cli db upgrade --revision 0002
run_cli legacy-ogc validate
run_cli db upgrade --revision 0003

after=$(psql_in "$name" -Atc "SELECT count(*) || '|' || min(ts) || '|' || max(ts) FROM analytics.access_logs;")
[ "$before" = "$after" ] || {
    echo "access_logs changed during migration: $before -> $after" >&2
    exit 1
}

state=$(psql_in "$name" -Atc "
    SELECT
        (SELECT version_num FROM analytics.alembic_version) || '|' ||
        (SELECT count(*) FROM timescaledb_information.continuous_aggregates
         WHERE view_schema = 'analytics' AND view_name LIKE 'ogc_summary_%_legacy') || '|' ||
        (SELECT count(*) FROM analytics.ogc_summary) || '|' ||
        (SELECT count(*) FROM analytics.ogc_summary_hourly_store);
")
case "$state" in
    0003\|3\|[1-9]*\|[1-9]*) ;;
    *) echo "Unexpected cutover state: $state" >&2; exit 1 ;;
esac

run_cli db downgrade --revision 0002
restored=$(psql_in "$name" -Atc "
    SELECT count(*) FROM timescaledb_information.continuous_aggregates
    WHERE view_schema = 'analytics'
      AND view_name IN ('ogc_summary_hourly', 'ogc_summary_daily', 'ogc_summary_monthly');
")
[ "$restored" = "3" ]

run_cli db upgrade --revision 0003
run_cli legacy-ogc validate
echo "Existing TimescaleDB $source_version -> $target_version migration OK."
