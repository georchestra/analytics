#!/bin/sh

set -eu
. "$(dirname -- "$0")/lib.sh"

require_command docker

max_size=1048576
(
    cd "$TEST_ROOT/fixtures/dumps"
    sha256sum -c SHA256SUMS
)
for version in 2.26.1 2.30.2; do
    fixture="$TEST_ROOT/fixtures/dumps/existing-timescaledb-${version}.dump"
    test -r "$fixture" || {
        echo "Missing fixture: $fixture" >&2
        exit 1
    }
    size=$(wc -c <"$fixture")
    [ "$size" -le "$max_size" ] || {
        echo "Fixture exceeds 1 MiB: $fixture ($size bytes)" >&2
        exit 1
    }
    listing=$(docker run --rm \
        -v "$TEST_ROOT/fixtures/dumps:/fixtures:ro" \
        "timescale/timescaledb:${version}-pg18" \
        pg_restore -l "/fixtures/existing-timescaledb-${version}.dump")
    printf '%s\n' "$listing" | grep -q 'TABLE analytics access_logs'
    printf '%s\n' "$listing" | grep -q 'VIEW analytics ogc_summary_hourly'
    strings "$fixture" | grep -Eq 'fixture|timescaledb|analytics'
    echo "Verified $fixture ($size bytes)"
done
