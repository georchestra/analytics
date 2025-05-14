import hashlib
import logging
import random
from datetime import datetime
from typing import Any

from georchestra_analytics_cli.access_logs.log_parsers.BaseLogParser import BaseLogParser
from georchestra_analytics_cli.config import Config
from georchestra_analytics_cli.utils import split_query_string, dict_recursive_update

logger = logging.getLogger(__name__)

fake_data = {
    "users": [
        {"name": "testadmin", "org": "PSC", "roles": ["ROLE_SUPERUSER", "ROLE_MAPSTORE_ADMIN"]},
        {"name": "testuser", "org": "C2C", "roles": ["ROLE_USER"]},
        {"name": "testuser2", "org": "G2F", "roles": ["ROLE_GEOSERVER_G2F", "ROLE_USER"]},
        {"name": "testeditor", "org": "PSC", "roles": ["ROLE_SUPERSET_ADMIN", "ROLE_USER"]},
    ],
    "requests": [
        {
            "app_path": "geoserver",
            "request_method": "GET",
            "request_path": "/geoserver/boundaries/ows",
            "request_query_string": "service=wms&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=frontieres_nationales&STYLES=boundaries%3ALines_Borders&CRS=EPSG%3A3857&WIDTH=2304&HEIGHT=1084&BBOX=715133.0164035556%2C6042414.756063141%2C1074822.6263080558%2C6211643.721834183",
            "response_size": 77735,
        },
        {
            "app_path": "geoserver",
            "request_method": "GET",
            "request_path": "/geoserver/environment/ows",
            "request_query_string": "service=wms&version=1.3.0&request=GetCapabilities",
            "response_size": 19834,
        },
        {
            "app_path": "geoserver",
            "request_method": "GET",
            "request_path": "/geoserver/ows",
            "request_query_string": "service=wms&version=1.3.0&request=GetCapabilities",
            "response_size": 19834,
        },
        {
            "app_path": "geoserver",
            "request_method": "GET",
            "request_path": "/geoserver/basemaps/ows",
            "request_query_string": "VERSION=1.1.1&SERVICE=WMS&REQUEST=GetMap&LAYERS=mnt_dem&STYLES=&SRS=EPSG:4326&BBOX=5.804821737,46.484411957778,9.808502599,50.108964044022&WIDTH=400&HEIGHT=362&FORMAT=image/jpeg",
            "response_size": 2645,
        },
        {
            "app_path": "geoserver",
            "request_method": "GET",
            "request_path": "/geoserver/environment/ows",
            "request_query_string": "VERSION=1.1.1&SERVICE=WMS&REQUEST=GetMap&LAYERS=parc_naturel&STYLES=&SRS=EPSG:4326&BBOX=6.3621425628662,47.041770975692,9.1019554138184,49.61293796662&WIDTH=400&HEIGHT=375&FORMAT=image/jpeg",
            "response_size": 45005,
        },
        {
            "app_path": "geoserver",
            "request_method": "GET",
            "request_path": "/geoserver/boundaries/ows",
            "request_query_string": "service=wms&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=boundaries%3Alimite_crs&STYLES=boundaries%3AContour_CRS_DE&CRS=EPSG%3A3857&WIDTH=1795&HEIGHT=1344&BBOX=838611.299727416%2C5973362.915505013%2C1032192.094065148%2C6118305.861237555",
            "response_size": 109946,
        },
    ],
    "status_codes": [200, 200, 200, 200, 200, 200, 200, 200, 404, 501],

}


class FakeLogGenerator(BaseLogParser):
    """
    This class is responsible for generating fake log records for testing or simulation
    purposes.

    The FakeLogGenerator processes and creates log records based on input configuration
    provided during the instantiation and additional parameters passed for parsing.
    It uses randomized data to produce various log fields, ensuring variability in the
    generated records. The class provides functionality for simulating logs for
    app-specific requirements through additional processing.
    """

    config: Config = None
    hashl = None

    def __init__(self, config: config):
        self.config = config
        # hashlib is used to generate a hashed key identifying the log message so that we can handle duplicates
        self.hashl = hashlib.md5()
        super().__init__(config)


    def parse(self, date: datetime) -> dict[str, Any]:
        """
        Generate a fake log record for the given date.
        """
        user = random.choice(fake_data["users"])
        req = random.choice(fake_data["requests"])
        log_dict = {
            "ts": date.isoformat(),
            "id": self.generate_req_id(date.isoformat()),
            "message": f"{date.isoformat()} GET {req.get('request_path')}?{req.get('request_query_string')} {req.get('response_size')}",
            "app_path": req.get("app_path"),
            "app_name": self.config.what_app_is_it(req.get("app_path")),
            "user_id": user.get("name"),
            "user_name": user.get("name"),
            "org_id": user.get("org"),
            "org_name": user.get("org"),
            "roles": user.get("roles"),
            "auth_method": None,
            "request_method": "GET",
            "request_path": req.get("request_path").lower(),
            "request_query_string": req.get("request_query_string").lower(),
            "request_details": split_query_string(req.get("request_query_string").lower()),
            "response_time": random.randint(50, 2000),
            "response_size": req.get("response_size"),
            "status_code": random.choice(fake_data["status_codes"]),
            "context_data": {
                "source_type": "fake_log_file",
            }
        }

        # And then add app-specific logic
        if log_dict.get("app_path", None) and log_dict.get("app_name", None):
            lp = self._get_app_processor(log_dict["app_name"], log_dict["app_path"])
            if not (lp and lp.is_relevant(log_dict["app_path"], log_dict.get("request_query_string", ""))):
                return None
            app_data = lp.collect_information(log_dict.get("request_path", ""), log_dict.get("request_details", {}))
            if app_data is not None:
                # We replace the request_details dict, instead of simplfy updating it. It allows to drop some values deemed uninteresting/redundant
                # dict_recursive_update(log_dict["request_details"], app_data)
                log_dict["request_details"] = app_data
        return log_dict

    def generate_req_id(self, msg):
        """
        Generate an ID for this log line. Will serve to avoid inserting duplicates. Replaces the span_id that we get
        with OpenTelemetry
        """
        self.hashl.update(msg.encode('utf-8'))
        return self.hashl.hexdigest()[0:12]

