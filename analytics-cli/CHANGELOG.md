
# Changelog

# Unreleased

* WMTS RESTful encoding support (GeoServer/GeoWebCache templates): tiles, feature info and capabilities requests are now tracked like their KVP counterpart
* WMTS REST templates are configurable per app processor (`wmts_rest_templates`), using the ResourceURL syntax of the WMTS capabilities
* OGC requests answered with a redirection (301, 302, 303, 307, 308) are no longer counted in the OGC views, since the target request is counted too. Configurable per app processor (`ignored_status_codes`)
* use psycopg (v3) instead of psycopg2: SQLAlchemy 2.1 made it the default driver for `postgresql://` URLs
* buffer2db: errors are now logged with their traceback and make the command exit with a non-zero code

# version 2.1.0

* adding config/analytics_cli.yaml into python package by @jeanmi151 in https://github.com/georchestra/analytics/pull/24
* analytics_cli run in loop with cron by @jeanmi151 in https://github.com/georchestra/analytics/pull/25


## version 1.0.x

- **bugfix**: Fixed `ON CONFLICT` error by removing duplicate index definition in SQLAlchemy models
- Fixed unique constraint on `(ts, id)` to work properly with TimescaleDB hypertables
- Add support for ogc api features from geoserver (missing support for mapserver and mapproxy for now)

## version 1.0.0

- **documentation** 
- improved timezone support
- data privacy minimal support

## Version 0.2.0

- **Extended OGC support** (geoserver, mapserver, mapproxy)
- external apps support, including when served on root path
- manage records from multiple domains
- Added new fields: client_ip, server_address, app_id

## Version 0.1.0

- Supports opentelemetry-like db table, file-based text logs and fake logs
- Log processor implemented (partially) for geoserver (misses for instance ogc-api support)
