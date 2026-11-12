#!/bin/sh

set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/analytics-cli.yaml" >&2
    exit 2
fi

command -v analytics-cli >/dev/null 2>&1 || {
    echo "analytics-cli is not available in PATH." >&2
    exit 1
}

config=$1
test -r "$config" || {
    echo "Configuration file is not readable: $config" >&2
    exit 1
}

echo "Checking database connectivity and current Alembic revision..."
analytics-cli --config-file "$config" db current

echo "Checking whether the schema can be safely adopted at baseline 0001..."
analytics-cli --config-file "$config" db check-baseline

echo "Read-only preflight completed. No database objects or revisions were changed."
