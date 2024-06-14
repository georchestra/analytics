#!/bin/bash
#
# Load a bunch of data into the DB. Beware that running it twice will insert duplicates.
# If necessary, you can purge the logs table using the SQL command `truncate analytics.logs`;
#

ACCESS_LOG_PATH=sample_data/traefik
for f in `ls -1 ${ACCESS_LOG_PATH}/access.log*`; do
  python3 cli.py process-logs --pghost localhost --pgport 55432 --pgname georchestra --pguser georchestra --pgpassword georchestra --pgtable analytics.logs $f
done