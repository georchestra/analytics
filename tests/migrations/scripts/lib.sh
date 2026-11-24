#!/bin/sh

set -eu

TEST_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$TEST_ROOT/../.." && pwd)
DB_USER=tsdb
DB_NAME=analytics
DB_PASSWORD=${MIGRATION_TEST_DB_PASSWORD:-migration-test}
DB_PORT=${MIGRATION_TEST_DB_PORT:-55435}
CLI=${ANALYTICS_CLI:-analytics-cli}
CONFIG="$TEST_ROOT/config/analytics-cli.yaml"

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

remove_container() {
    name=$1
    docker rm -f "$name" >/dev/null 2>&1 || true
}

remove_volume() {
    name=$1
    docker volume rm "$name" >/dev/null 2>&1 || true
}

wait_for_database() {
    name=$1
    attempts=0
    # The Docker entrypoint starts a temporary Unix-socket-only PostgreSQL
    # server while initializing the data directory. Checking without --host can
    # observe that server just before it shuts down, causing the first external
    # CLI connection to race with the final startup. TCP is available only from
    # the definitive server used by the tests.
    until docker exec "$name" pg_isready -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge 90 ]; then
            docker logs "$name" >&2
            echo "Database did not become ready: $name" >&2
            exit 1
        fi
        sleep 1
    done
}

psql_in() {
    name=$1
    shift
    docker exec "$name" psql -X -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" "$@"
}

run_cli() {
    MIGRATION_TEST_DB_PASSWORD="$DB_PASSWORD" MIGRATION_TEST_DB_PORT="$DB_PORT" \
        "$CLI" --config-file "$CONFIG" "$@"
}

start_database() {
    name=$1
    volume=$2
    image=$3
    remove_container "$name"
    docker run -d --name "$name" \
        -p "127.0.0.1:$DB_PORT:5432" \
        -e POSTGRES_DB="$DB_NAME" \
        -e POSTGRES_USER="$DB_USER" \
        -e POSTGRES_PASSWORD="$DB_PASSWORD" \
        -v "$volume:/var/lib/postgresql" \
        "$image" >/dev/null
    wait_for_database "$name"
}
