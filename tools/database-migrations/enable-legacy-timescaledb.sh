#!/bin/sh

set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/analytics-cli.yaml" >&2
    exit 2
fi

analytics-cli --config-file "$1" legacy-ogc enable
