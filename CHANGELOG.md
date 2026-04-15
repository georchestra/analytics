
# Changelog

## Version 2.0.0

- [Decided](https://github.com/georchestra/improvement-proposals/issues/11#issuecomment-4045295516) to start versioning at v2 (v1 referring to old analytics module)
- [ogc-api support](https://github.com/georchestra/analytics/pull/8)
- [removed dependency on timescaledb-toolkit package](https://github.com/georchestra/analytics/commit/d67f639327ee0bc9feb7f8319b8989cb130e5527)
- [refactored documentation](https://github.com/georchestra/analytics/commit/f3a5156df1fc39832544a6a40d96d7829b6600db)
- bugfixes for regex parsing
- added referrer and user-agent graphs

## Version 1.0.0

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
