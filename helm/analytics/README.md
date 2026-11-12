_Work in progress_

See https://docs.georchestra.org/analytics/technical_guides/installation/

## Database migrations

The chart runs an Alembic migration Job after every Helm install and upgrade.
The Job upgrades the schema to `head` and then synchronizes the configured
TimescaleDB policies. It is retried while the database becomes available.

New installations require no additional settings:

```yaml
cli:
  migrations:
    enabled: true
    targetRevision: head
```

When upgrading an existing, pre-Alembic installation, opt in to the baseline
step for the first deployment:

```yaml
cli:
  migrations:
    existingDatabase:
      enabled: true
      baselineRevision: "0001"
```

`bootstrap-existing` refuses to stamp the database if any expected `0001`
relation is missing. If the database already has an Alembic revision, the
baseline step is skipped, so leaving the option enabled cannot move the
recorded revision backwards. Disable the option again after adoption to keep
the deployment intent clear.

The migration is a regular Kubernetes Job created together with the built-in
TimescaleDB instance. Its name includes the Helm release revision, so every
install or upgrade gets a new idempotent migration run. Do not convert it into
a `post-install` hook: with `helm --wait`, that would deadlock because Vector's
revision gate cannot become ready before the hook is started.

While migrations are enabled, the chart does not mount the former SQL
entrypoint scripts into the built-in database. Alembic is the single schema
owner. Vector and both CLI CronJobs use an init container that runs
`analytics-cli db require-revision`; they cannot produce or process records
until the database has reached `cli.migrations.targetRevision`.

The default built-in database is TimescaleDB 2.30.2 on PostgreSQL 18. Its PVC is
mounted at `/var/lib/postgresql`, as required by the PostgreSQL 18 image layout.
The chart targets the `georchestra/analytics-cli:2.2.0` release image, which must
be published before deploying this chart version. Published 2.1.x images do not
contain these migrations or the revision gate command.

Setting `cli.migrations.enabled: false` restores the legacy SQL entrypoint
mounts for compatibility only; it is not the supported path for new 2.2.0
installations.

The complete chart and cutover lifecycle can be exercised locally with
`make test-helm-k3d`. It performs repeated validation, disables the legacy jobs,
checks their TimescaleDB scheduling state, and enables them again. It never
removes the legacy continuous aggregates.

## Incremental OGC aggregation

The chart creates a separate recovery CronJob for the persistent OGC aggregation
queue. `buffer2db` already drains this queue after ingestion; the additional job
retries pending buckets and processes buckets queued by `file2db` or `fake2db`.

```yaml
cli:
  aggregation:
    enabled: true
    schedule: "15 * * * *"
    batchSize: 100
    backoffLimit: 2
    successfulJobsHistoryLimit: 1
    failedJobsHistoryLimit: 3
```

The CronJob runs `analytics-cli aggregate-ogc`. Successful transactions remove
their queue rows. Historical retention and removal of the legacy TimescaleDB
continuous aggregates are intentionally outside this job and belong to the final
cutover procedure.
