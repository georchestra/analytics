#!/bin/sh

set -eu
. "$(dirname -- "$0")/lib.sh"

require_command docker

OUTPUT="$TEST_ROOT/fixtures/dumps"
mkdir -p "$OUTPUT"

generate_fixture() {
    version=$1
    image="timescale/timescaledb:${version}-pg18"
    name="analytics-fixture-${version%%.*}-${version#*.}"
    name=$(printf '%s' "$name" | tr '.' '-')

    remove_container "$name"
    docker run -d --name "$name" \
        -e POSTGRES_DB="$DB_NAME" \
        -e POSTGRES_USER="$DB_USER" \
        -e POSTGRES_PASSWORD="$DB_PASSWORD" \
        "$image" >/dev/null
    wait_for_database "$name"

    docker exec -i "$name" psql -X -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" \
        <"$REPO_ROOT/config/analytics/db.entrypoints.d/100_analytics_init.sql"
    docker exec -i "$name" psql -X -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" \
        <"$REPO_ROOT/config/analytics/db.entrypoints.d/101_analytics_ogc_views.sql"
    psql_in "$name" -c "SELECT alter_job(job_id, scheduled => false) FROM timescaledb_information.jobs WHERE hypertable_schema = 'analytics';"
    docker exec -i "$name" psql -X -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" \
        <"$TEST_ROOT/fixtures/seed.sql"

    output="$OUTPUT/existing-timescaledb-${version}.dump"
    docker exec "$name" pg_dump -Fc -U "$DB_USER" -d "$DB_NAME" >"$output"
    remove_container "$name"
    echo "Generated $output ($(wc -c <"$output") bytes)"
}

trap 'remove_container analytics-fixture-2-26-1; remove_container analytics-fixture-2-30-2' EXIT INT TERM

generate_fixture 2.26.1
generate_fixture 2.30.2
(
    cd "$OUTPUT"
    sha256sum existing-timescaledb-2.26.1.dump \
        existing-timescaledb-2.30.2.dump >SHA256SUMS
)
"$TEST_ROOT/scripts/verify-fixtures.sh"
