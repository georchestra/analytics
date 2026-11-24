# Database migrations

Database schema changes are managed by Alembic through `analytics-cli db`.
Fresh installations can upgrade directly to `head`. Existing installations
created from the former SQL initialization scripts must first adopt revision
`0001` without replaying its DDL.

The migration has three relevant revisions:

- `0001`: baseline matching the former manually initialized schema;
- `0002`: persistent OGC hourly, daily, and monthly stores plus the incremental queue;
- `0003`: compatibility cutover from TimescaleDB continuous aggregates to the persistent stores.

Operational scripts are available in `tools/database-migrations`. They are
deliberately explicit: permanent removal of legacy aggregates is never part of
the normal migration command.

Read these guides in order:

1. [Existing installations](existing-installations.md)
2. [TimescaleDB upgrade](timescaledb-upgrade.md)
3. [Validation and cutover](validation-and-cutover.md)
4. [Rollback](rollback.md)
