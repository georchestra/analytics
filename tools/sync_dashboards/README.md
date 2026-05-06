# sync-dashboards

Syncs Superset dashboard `.zip` exports to a running Superset instance via its REST API.

- **Idempotent**: only imports when the zip file hash has changed (tracked as a `zip-sha256:` tag on the dashboard in Superset)
- **Preserves IDs**: uses `overwrite=true` so dashboards matched by UUID keep their Superset IDs
- **URI patching**: optionally replaces `sqlalchemy_uri` in the zip's database configs at import time (no file modified on disk)
- **Two auth modes**: geOrchestra sec-headers (default) or classic username/password login

## Requirements

- Python >= 3.11
- `requests` library

## Run locally

```bash
cd tools/sync_dashboards

# install dependencies
pip install -r requirements.txt

# run with geOrchestra auth (default)
python sync_dashboards.py \
    --superset-url http://localhost:8088/superset/ \
    --dashboards-dir ../../dashboards/superset \
    --db-uri 'postgresql://tsdb:password@timescaledb:5432/analytics'

# run with classic auth
python sync_dashboards.py \
    --superset-url http://localhost:8088 \
    --username admin \
    --password admin \
    --dashboards-dir ../../dashboards/superset
```

## Build the Docker image

The build context must be the **repository root** because the Dockerfile copies
both the script and the dashboard zips from `dashboards/superset/`.

```bash
# from the repository root
docker build -t georchestra/analytics-syncdashboards -f tools/sync_dashboards/Dockerfile .
```

## Run with Docker

The dashboard zips are baked into the image at `/dashboards`, so no volume mount
is needed.

```bash
docker run --rm \
    -e SUPERSET_URL=http://superset:8088/superset/ \
    -e ANALYTICS_DB_URI='postgresql://tsdb:password@timescaledb:5432/analytics' \
    georchestra/analytics-syncdashboards
```

## Configuration

All options can be set via CLI flags or environment variables.

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--superset-url` | `SUPERSET_URL` | `http://localhost:8088` | Superset base URL |
| `--dashboards-dir` | `DASHBOARDS_DIR` | `/dashboards` | Directory containing `.zip` exports |
| `--db-uri` | `ANALYTICS_DB_URI` | *(none)* | Override `sqlalchemy_uri` in database configs (see below) |
| `--force` | | `false` | Import even if the hash hasn't changed |
| `--verbose` / `-v` | | `false` | Debug logging |

### Database URI

If `--db-uri` / `$ANALYTICS_DB_URI` is not set, the URI is assembled from the
following env vars (all five must be set):

| Env var | Example |
|---------|---------|
| `TSDB_USER` | `tsdb` |
| `TSDB_PASSWORD` | `password` |
| `TSDB_HOST` | `timescaledb` |
| `TSDB_PORT` | `5432` |
| `TSDB_NAME` | `analytics` |

Result: `postgresql://$TSDB_USER:$TSDB_PASSWORD@$TSDB_HOST:$TSDB_PORT/$TSDB_NAME`

### geOrchestra auth (default)

| Flag | Env var | Default |
|------|---------|---------|
| `--sec-username` | `SEC_USERNAME` | `analytics_update` |
| `--sec-roles` | `SEC_ROLES` | `ROLE_SUPERSET_ADMIN` |
| `--sec-email` | `SEC_EMAIL` | `admin@example.com` |

### Classic auth

Providing `--username` (or `SUPERSET_USERNAME`) switches to username/password
login via `POST /api/v1/security/login`.

| Flag | Env var | Default |
|------|---------|---------|
| `--username` | `SUPERSET_USERNAME` | *(none)* |
| `--password` | `SUPERSET_PASSWORD` | *(none)* |

## CI/CD

The GitHub Actions workflow at `.github/workflows/build-sync-dashboards.yml`
rebuilds the image on pushes to `main` when any of these paths change:

- `tools/sync_dashboards/**`
- `dashboards/superset/**`
- `.github/workflows/build-sync-dashboards.yml`
