# Validation and cutover

Revision `0002` creates ordinary PostgreSQL stores alongside the legacy
continuous aggregates. It copies the currently visible hourly, daily, and
monthly results and validates row counts, request totals, ranges, and values.

Before revision `0003`, run:

```bash
analytics-cli --config-file /path/to/analytics-cli.yaml aggregate-ogc
analytics-cli --config-file /path/to/analytics-cli.yaml legacy-ogc validate
```

Cutover is refused when the durable aggregation queue is not empty or a legacy
row is missing or different in the persistent store.

A bucket that fails three times remains in `analytics.ogc_aggregation_queue`
with its `attempts` and `last_error` values for operator inspection. It is then
skipped so healthy buckets continue processing, but it still blocks cutover.
After correcting the underlying data or configuration, reset `attempts` to zero
for that specific bucket and run `aggregate-ogc` again. Do not delete the queue
row merely to bypass validation.

Revision `0003` keeps the established `ogc_summary*` names as compatibility
views backed by the persistent stores. The former continuous aggregates are
renamed with a `_legacy` suffix and remain available for comparison.

After observing and comparing both mechanisms, pause the legacy jobs:

```bash
./tools/database-migrations/disable-legacy-timescaledb.sh /path/to/analytics-cli.yaml
```

Permanent removal is optional and must be a separate operational decision.
