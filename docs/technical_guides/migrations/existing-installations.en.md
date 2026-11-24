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

Revision `0002` deliberately queues recent raw OGC buckets after copying the
legacy aggregates. This reconciles records that were committed to `access_logs`
but had not yet been materialized by the legacy refresh policies. Revision
`0003` refuses the cutover until that queue has been drained successfully.

Do not run the migration while another process is writing analytics records.
Pause ingestion and scheduled analytics jobs for the maintenance window.

## Docker Compose storage compatibility

The Compose deployment deliberately retains the historical
`timescaledb_home_data` and `timescaledb_home_log` volume keys and the HA image
mount paths. `docker compose up` therefore reattaches the existing project
volumes instead of creating an unrelated empty database volume.

Before upgrading, verify the resolved project and volume names:

```bash
docker compose -f docker/docker-compose.analytics.yml \
  --env-file docker/.envs-analytics config
docker volume ls | grep timescaledb_home_data
```

Do not point a PostgreSQL image from a different major version at that physical
volume. A major-version change requires a logical dump/restore or `pg_upgrade`
performed by the database operator. After starting the compatible PostgreSQL
major version, update and verify the TimescaleDB extension as described in the
[TimescaleDB upgrade guide](timescaledb-upgrade.en.md), then run the Alembic
migration workflow above.
