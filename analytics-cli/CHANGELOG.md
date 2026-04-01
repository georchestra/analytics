
# Changelog

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
