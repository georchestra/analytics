#!/bin/sh

set -eu
. "$(dirname -- "$0")/lib.sh"

require_command docker

compose_file="$REPO_ROOT/docker/docker-compose.analytics.yml"
env_file="$REPO_ROOT/docker/.envs-analytics"
rendered=$(docker compose -f "$compose_file" --env-file "$env_file" config)

assert_rendered() {
    pattern=$1
    printf '%s\n' "$rendered" | grep -F -- "$pattern" >/dev/null || {
        echo "Rendered Compose file is missing: $pattern" >&2
        exit 1
    }
}

assert_rendered "source: timescaledb_home_data"
assert_rendered "target: /home/postgres/pgdata"
assert_rendered "source: timescaledb_home_log"
assert_rendered "target: /home/postgres/pg_log"

if printf '%s\n' "$rendered" | grep -F "source: timescaledb_data" >/dev/null; then
    echo "Rendered Compose file still references the incompatible renamed volume" >&2
    exit 1
fi

echo "Docker Compose preserves the historical TimescaleDB volumes."
