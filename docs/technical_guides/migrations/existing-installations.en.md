# Existing installations

Back up the database and verify the TimescaleDB version before running Alembic.
The supported target used by the migration validation suite is TimescaleDB
2.30.2 on PostgreSQL 18.

Run the preflight command with the same configuration used by the analytics CLI:

```bash
./tools/database-migrations/preflight.sh /path/to/analytics-cli.yaml
```

The preflight uses the read-only `db check-baseline` command. During the actual
migration, `db bootstrap-existing` stamps only an unversioned database and
becomes a no-op when an Alembic revision is already recorded. It never recreates
tables or moves a recorded revision backwards.

After a successful preflight, run:

```bash
./tools/database-migrations/migrate-existing.sh /path/to/analytics-cli.yaml
```

This applies `0002`, compares the legacy aggregates with the persistent stores,
drains the incremental queue, applies the `0003` compatibility cutover, and
synchronizes configured TimescaleDB policies.

Do not run the migration while another process is writing analytics records.
Pause ingestion and scheduled analytics jobs for the maintenance window.
