#!/bin/sh

set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/analytics-cli.yaml" >&2
    exit 2
fi

config=$1

analytics-cli --config-file "$config" db bootstrap-existing --revision 0001
analytics-cli --config-file "$config" db upgrade --revision 0002
analytics-cli --config-file "$config" aggregate-ogc
analytics-cli --config-file "$config" legacy-ogc validate
analytics-cli --config-file "$config" db upgrade --revision 0003
analytics-cli --config-file "$config" db sync-policies
analytics-cli --config-file "$config" db current
