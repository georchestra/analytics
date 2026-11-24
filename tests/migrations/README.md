# Database migration integration tests

This suite validates fresh installation, adoption of a pre-Alembic database,
TimescaleDB 2.26.1 to 2.30.2 upgrade, OGC compatibility cutover, rollback, and
reapplication.

The committed dumps contain only synthetic documentation-safe values. They are
generated from `fixtures/seed.sql` and never contain records copied from a
customer database. Regenerate and verify them with:

```bash
make migration-fixtures
make verify-migration-fixtures
```

Run the integration scenarios with:

```bash
make test-migrations-fresh
make test-migrations-existing
make test-migrations-timescaledb-upgrade
make test-migrations-all
```

Docker, PostgreSQL client tools, and an installed `analytics-cli` are required.
The tests create isolated containers and Docker volumes and remove them on exit.

Large real-world dumps are deliberately excluded from Git. Use the external
dump laboratory described in `real-dump/README.md` for release rehearsals.
