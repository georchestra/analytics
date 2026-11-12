# Database migration tools

These scripts provide an explicit operational path for adopting the Alembic
schema on an existing geOrchestra Analytics database. They do not manage the
PostgreSQL or TimescaleDB server upgrade itself; that operation depends on the
deployment platform and must be completed before Alembic migration.

The supported sequence is:

```bash
./tools/database-migrations/preflight.sh /path/to/analytics-cli.yaml
./tools/database-migrations/migrate-existing.sh /path/to/analytics-cli.yaml
./tools/database-migrations/validate-cutover.sh /path/to/analytics-cli.yaml
./tools/database-migrations/disable-legacy-timescaledb.sh /path/to/analytics-cli.yaml
```

Permanent removal is intentionally separate and requires an exact confirmation
token:

```bash
./tools/database-migrations/drop-legacy-timescaledb.sh \
  /path/to/analytics-cli.yaml DROP_LEGACY_OGC_AGGREGATES
```

Read the [published migration guide](../../docs/technical_guides/migrations/index.en.md)
before using these scripts on a production database.
