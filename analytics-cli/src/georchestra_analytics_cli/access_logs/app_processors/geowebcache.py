"""
Process log files for a standalone GeoWebCache app
GeoWebCache serves the same services as the one integrated in GeoServer (without the /gwc prefix):
it reuses the GeoServer processor, but is recorded under its own app name (geowebcache)
"""

from georchestra_analytics_cli.access_logs.app_processors.geoserver import (
    GeoserverLogProcessor,
)


class GeowebcacheLogProcessor(GeoserverLogProcessor):
    app_path: str = "geowebcache"
