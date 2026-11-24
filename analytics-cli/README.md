# geOrchestra analytics CLI

A CLI tool to process access log data for geOrchestra analytics.

Different sources are accepted for access log data:
- A postgresql buffer table reproducing the Opentelemetry access log data structure.
- File-based access logs. It is expected to contain CLF-like (or, say, text-based) access log entries. They are parsed using a regular expression pattern. 
- Fake access logs can also be generated for dev/testing/discovery purposes

The result is written in a postgresql table, preferably a timescaleDB hypertable, since a lot of data will be written and you will want time-enabled data management.

To know more about it, please read the doc on https://docs.georchestra.org/analytics

## Install

Create a virtualenv and install this package:
```bash
python -m venv .venv
source .venv/bin/activate
pip install georchestra_analytics_cli
```


## Database migrations

Schema migrations are managed with [Alembic](https://alembic.sqlalchemy.org/) via the `analytics-cli db` subcommands.

### Existing production database

The schema was previously created by the Docker entrypoint SQL files. After verifying
that it matches the `0001` baseline, tell Alembic to treat that revision as already
applied, without running any DDL:

```bash
analytics-cli --config-file /path/to/config.yaml db stamp --revision 0001
```

For automated deployments, prefer the idempotent baseline command. It checks
that the expected baseline relations exist, stamps only an unversioned
database, and skips databases that already have an Alembic revision:

```bash
analytics-cli --config-file /path/to/config.yaml db bootstrap-existing --revision 0001
```

To perform the same compatibility check without recording a revision, use the
read-only preflight command:

```bash
analytics-cli --config-file /path/to/config.yaml db check-baseline
```

Verify:
```bash
analytics-cli --config-file /path/to/config.yaml db current
# → Rev: 0001 (head)
```

Never use `stamp head` for this adoption step: once later revisions exist, that would
mark unapplied schema and data migrations as completed. From this point on, use
`db upgrade` whenever a new release includes migrations.

### Local development (fresh database)

If the `analytics` schema doesn't exist yet (e.g. a plain PostgreSQL instance without the Docker setup), run all migrations from scratch:

```bash
analytics-cli --config-file /path/to/config.yaml db upgrade
```

This creates the schema, tables, and all TimescaleDB objects in one step.

The `0001` core baseline contains the OGC aggregates deployed by the Helm chart.
The optional Data API aggregates are intentionally excluded because they require
Timescale Toolkit, which is not bundled in that TimescaleDB image.

Revision `0002` creates persistent OGC stores and seeds them from the existing
continuous aggregates. It deliberately leaves the continuous aggregates and their
policies unchanged; application dual-write and query cutover are separate release
steps.

The CLI dual-run implementation queues affected hourly buckets in the same
transaction that writes `access_logs`. `buffer2db` then drains the queue and
recomputes the persistent hourly, local-calendar daily, and local-calendar monthly
stores. A failed buffer batch is rolled back as a unit, so its source rows remain in
`opentelemetry_buffer` for retry.

The queue can also be drained independently, which is useful for recovery or a
separate scheduled job:

```bash
analytics-cli --config-file /path/to/config.yaml aggregate-ogc
analytics-cli --config-file /path/to/config.yaml aggregate-ogc --batch-size 100
```

`file2db` and `fake2db` enqueue affected buckets through the same transactional
write path. Their queue is processed by the next `buffer2db` or `aggregate-ogc` run.
The per-transaction limit defaults to:

```yaml
performance:
  ogc_aggregation_batch_size: 100
```

Revision `0003` performs the query cutover. It renames the three TimescaleDB
continuous aggregates with a `_legacy` suffix and creates ordinary compatibility
views with the established `ogc_summary*` names, backed by the persistent stores.
Superset and other clients therefore keep the same interface.

Before cutover, compare both implementations and drain the queue:

```bash
analytics-cli --config-file /path/to/config.yaml aggregate-ogc
analytics-cli --config-file /path/to/config.yaml legacy-ogc validate
analytics-cli --config-file /path/to/config.yaml db upgrade --revision 0003
```

After cutover, the legacy jobs can be paused without deleting data and restored if
rollback is needed:

```bash
./scripts/disable-legacy-timescaledb.sh /path/to/config.yaml
./scripts/enable-legacy-timescaledb.sh /path/to/config.yaml
```

Permanent removal is deliberately separate and requires an exact confirmation:

```bash
./scripts/drop-legacy-timescaledb.sh \
  /path/to/config.yaml DROP_LEGACY_OGC_AGGREGATES
```

That command removes only the three legacy OGC continuous aggregates and their
attached policies/jobs. It does not remove the TimescaleDB extension or the
`access_logs` hypertable. Removing them is irreversible: downgrade from `0003` to
`0002` is intentionally refused afterward.

> **Note:** On a plain PostgreSQL instance (no TimescaleDB extension), the initial revision will fail at the `create_hypertable` call. Either use the TimescaleDB Docker image, or stamp at `0001` after manually creating the schema and run only subsequent revisions.

### Applying future migrations

After upgrading to a new version:

```bash
analytics-cli --config-file /path/to/config.yaml db upgrade
analytics-cli --config-file /path/to/config.yaml db sync-policies
```

The second command reconciles the operational TimescaleDB settings for
`analytics.access_logs`. These settings are configurable independently from the
immutable Alembic baseline:

```yaml
database:
  timescaledb:
    chunk_interval: "7 days"
    retention:
      drop_after: "3 years"
      schedule_interval: "1 week"
```

`chunk_interval` applies to chunks created after synchronization; it does not resize
existing chunks. Running `db sync-policies` repeatedly is safe. The retention job is
left untouched when its intervals already match the configuration, and is replaced
transactionally when either interval changes.

### Reference

| Command | Description |
|---------|-------------|
| `db current` | Show the revision the database is currently at |
| `db upgrade` | Apply all pending migrations up to `head` |
| `db upgrade --revision <rev>` | Apply migrations up to a specific revision |
| `db downgrade` | Roll back one migration |
| `db downgrade --revision <rev>` | Roll back to a specific revision |
| `db check-baseline` | Validate an existing schema against `0001` without modifying it |
| `db bootstrap-existing` | Validate and stamp only an unversioned existing database at `0001` |
| `db stamp` | Mark an existing database at baseline revision `0001` without running DDL |
| `db stamp --revision <rev>` | Mark the database at an explicit revision without running DDL |
| `db sync-policies` | Reconcile the configured `access_logs` chunk and retention intervals |

The `--config-file` option (or `GEORCHESTRA_ANALYTICS_CLI_CONFIG_FILE` env var) is required whenever the default config doesn't match your database connection.

### Writing migrations

New revision files go in `src/georchestra_analytics_cli/alembic/versions/`. Use `op.execute()` for all DDL — TimescaleDB-specific operations (hypertables, continuous aggregates, retention/compression policies) have no SQLAlchemy ORM equivalent and must remain raw SQL.

#### Changing OGC aggregate definitions

Do not drop and recreate an existing OGC continuous aggregate. Retention may already
have removed source rows from `access_logs`, so the historical aggregate can contain
data that cannot be rebuilt. Disabling retention while recreating the aggregate does
not recover those deleted source rows.

| Scenario | What to do |
|----------|------------|
| New column on `access_logs` not used by OGC views | Nothing — views stay valid |
| OGC aggregate query changes | Create persistent replacement tables and migrate/validate the existing aggregate data before cutover |
| Only policy changes (retention interval, schedule) | `remove_*_policy` + `add_*_policy`, no drop |

## Build & publish

This project is based on [pyScaffold](https://pypi.org/project/PyScaffold/) and uses [tox](https://tox.wiki/en/latest/installation.html) for the build.

There is no CI as of now, it's done manually.

To install `tox`, we recommend installing it with [pipx](https://pypi.org/project/pipx):
```bash
pipx install tox
tox --help
```

### Build the project:
```bash
tox -e clean,build
```

### Publish to Pypi:
To publish to Pypi, there are some prerequisites:

- You must set a git tag on your current commit (e.g. `git tag -a 0.1.0 -m "v0.1.0"`)
- Your git working tree should be clean (nothing pending, `git status` should report `nothing to commit, working tree clean`).

This ensures that `setuptools_scm` will detect a clean version. `setuptools_scm` extracts automatically the version from the `git describe` information, behind the scene.

You will also also need a pypi token to publish

Publish on test.pypi.org:
```bash
tox -e publish
```

Publish on pypi.org:
```bash
tox -e publish -- --repository pypi
```

### Docker build:

We provide you with a utility script, `./docker_build.sh`.  
It takes 2 options:

- `--mode=`: the build mode (one of [dev, test, pypi]). `test` will try to fetch the package from test.pypi while `pypi` will try to fetch it from the main pypi repo. `dev` will build the local code base.
- `--version=`: allows to set the version to use. On dev mode, it can be arbitrary. 

Examples:

- Build from the latest version from pypi:
```bash
./docker_build.sh --mode=release
```
- Build from the 2.1.1 version from pypi: (version 2.1.1 has to exist there)
```bash
./docker_build.sh --mode=release --version=2.1.1
```
- Build from the 2.1.1 version from test.pypi: (version 2.1.1 has to exist there)
```bash
./docker_build.sh --mode=test --version=2.1.1
```
- Build from local codebase, tag it 2.1.1-dirty:
```bash
./docker_build.sh --mode=dev --version=2.1.1-dirty
```
- Build from local codebase, use the auto-generated tag:
```bash
./docker_build.sh --mode=dev
```
