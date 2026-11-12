#!/bin/sh

set -eu

if [ "$#" -ne 2 ] || [ "$2" != "DROP_LEGACY_OGC_AGGREGATES" ]; then
    echo "Usage: $0 /path/to/analytics-cli.yaml DROP_LEGACY_OGC_AGGREGATES" >&2
    exit 2
fi

analytics-cli --config-file "$1" legacy-ogc validate
analytics-cli --config-file "$1" legacy-ogc drop --confirm "$2"
