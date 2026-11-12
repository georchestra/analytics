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

echo "Fresh database upgrade to Alembic head OK."
