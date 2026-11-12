# TimescaleDB upgrade before Alembic

The TimescaleDB server and extension must be upgraded before applying the
Alembic migration. The exact server upgrade procedure depends on whether the
database is managed through Kubernetes, Docker, system packages, or a hosted
service.

An archive containing TimescaleDB internal catalogs cannot safely be restored
directly into a different extension version. For example, a PostgreSQL 18 dump
created with TimescaleDB 2.26.1 fails when restored directly into 2.30.2 because
the internal catalog constraints changed.

For a backup-based rehearsal:

1. restore with the exact TimescaleDB source version;
2. stop PostgreSQL cleanly;
3. start the same PostgreSQL data volume with the target TimescaleDB image;
4. connect as a database owner and run:

    ```sql
    ALTER EXTENSION timescaledb UPDATE;
    ```

5. verify the installed version:

    ```sql
    SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';
    ```

6. run the Alembic preflight and migration only after the extension reports the
   supported target version.

For a live database, follow the official TimescaleDB upgrade procedure for the
deployment platform. Always rehearse the complete restore and upgrade against a
disposable copy first.
