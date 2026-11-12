# From 2.1.1 to 2.2.0

Version 2.2.0 replaces manual database schema changes with versioned Alembic
migrations. It also moves OGC statistics from retention-limited TimescaleDB
continuous aggregates to persistent PostgreSQL tables while preserving the
existing `analytics.ogc_summary*` query interface.

Read the complete [database migration guide](../../docs/technical_guides/migrations/index.en.md)
before upgrading a production installation.

## Database requirements

The validated upgrade target is:

- PostgreSQL 18;
- TimescaleDB 2.30.2 Community Edition;
- `analytics-cli` from the 2.2.0 release.

Upgrade the TimescaleDB server and extension before running Alembic. In
particular, a backup produced with TimescaleDB 2.26.1 and containing TimescaleDB
internal catalogs must first be restored with 2.26.1. Restart the same database
volume with 2.30.2 and then run:

```sql
ALTER EXTENSION timescaledb UPDATE;
SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';
```

The second query must report `2.30.2` before continuing. See the
[TimescaleDB upgrade guide](../../docs/technical_guides/migrations/timescaledb-upgrade.en.md)
for the backup rehearsal and live-upgrade requirements.

## Preparation

1. Create and verify a complete database backup.
2. Rehearse the restore and migration against a disposable copy.
3. Schedule a maintenance window.
4. Pause log ingestion and scheduled analytics processing.
5. Upgrade TimescaleDB to the validated target version.
6. Install and configure the 2.2.0 `analytics-cli`.

Run the read-only preflight check:

```bash
./tools/database-migrations/preflight.sh /path/to/analytics-cli.yaml
```

The check verifies database connectivity, the current Alembic revision, and the
relations required to adopt the former manually initialized schema as revision
`0001`. It does not change the database.

## Existing installation migration

Run the complete existing-installation workflow:

```bash
./tools/database-migrations/migrate-existing.sh /path/to/analytics-cli.yaml
```

The script performs these operations in order:

1. safely records baseline revision `0001` only when the database is still unversioned;
2. applies revision `0002` and creates persistent hourly, daily, and monthly OGC stores;
3. drains the incremental aggregation queue;
4. compares the legacy aggregates with the persistent stores;
5. applies revision `0003` and exposes the persistent stores through the established names;
6. synchronizes the configured TimescaleDB policies.

The migration preserves the original continuous aggregates with a `_legacy`
suffix. It does not remove TimescaleDB or the `analytics.access_logs` hypertable.

## Helm deployment

New installations run Alembic automatically through the Helm migration Job.
When adopting Alembic on an existing installation, enable the baseline step for
the first deployment:

```yaml
cli:
  migrations:
    enabled: true
    targetRevision: head
    existingDatabase:
      enabled: true
      baselineRevision: "0001"
```

The baseline command is idempotent and skips a database that already has an
Alembic revision. Disable `existingDatabase.enabled` after the adoption deploy
to make the deployment intent explicit.

The Helm chart blocks Vector and its CLI CronJobs until the migration Job has
recorded the configured target revision. With migrations enabled, the built-in
database is initialized exclusively by Alembic instead of the legacy SQL
entrypoint scripts. Publish the `georchestra/analytics-cli:2.2.0` image before
deploying the chart; the public 2.1.x CLI cannot execute this migration set.

## Validation and legacy job shutdown

Validate the migrated state before pausing the legacy calculation jobs:

```bash
./tools/database-migrations/validate-cutover.sh /path/to/analytics-cli.yaml
./tools/database-migrations/disable-legacy-timescaledb.sh /path/to/analytics-cli.yaml
```

Resume ingestion and monitor at least the hourly, daily, and monthly reporting
paths. Legacy jobs can be restored while the legacy aggregates still exist:

```bash
./tools/database-migrations/enable-legacy-timescaledb.sh /path/to/analytics-cli.yaml
```

Permanent removal is optional, irreversible, and must not be part of the first
2.2.0 deployment. After an independently approved observation period, it can be
performed with the explicitly confirmed command documented in
`tools/database-migrations/README.md`.

## Rollback

Before permanent legacy removal, return to revision `0002` with:

```bash
analytics-cli --config-file /path/to/analytics-cli.yaml \
  db downgrade --revision 0002
```

This restores the original continuous aggregate names and their previous job
state without deleting `analytics.access_logs` or the persistent stores. See the
[rollback guide](../../docs/technical_guides/migrations/rollback.en.md) for the
complete procedure and limitations.

## Automated validation

The repository contains small synthetic dumps for TimescaleDB 2.26.1 and
2.30.2. They contain no customer data and validate fresh installation, direct
2.30.2 adoption, 2.26.1 to 2.30.2 extension upgrade, Alembic cutover, rollback,
and reapplication:

```bash
make test-migrations-all
```

Large production dumps are deliberately excluded from the repository and must
remain in a secure external validation environment.
