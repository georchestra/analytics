# Rollback

Before legacy continuous aggregates are permanently removed, revision `0003`
can be rolled back:

```bash
analytics-cli --config-file /path/to/analytics-cli.yaml db downgrade --revision 0002
```

The downgrade removes the compatibility views, restores the original continuous
aggregate names, and restores the scheduled state of jobs paused through the
analytics CLI.

Reapply the cutover with:

```bash
analytics-cli --config-file /path/to/analytics-cli.yaml db upgrade --revision 0003
```

Rollback is intentionally refused after permanent legacy removal because the
continuous aggregates and their historical materialization no longer exist.
Persistent stores and `analytics.access_logs` are not removed by the `0003`
downgrade.
