"""
Process log files for the Mapproxy app
Inherits from the generic OGC server processor
"""

import logging
import re
from typing import Any

from georchestra_analytics_cli.access_logs.app_processors.ogcserver import OgcserverLogProcessor


class MapproxyLogProcessor(OgcserverLogProcessor):
    app_path: str = "mapproxy"

    def is_relevant(self, request_path: str, query_string: str) -> bool:
        """
        Check if the request matches a pattern corresponding to a query we want to track.
        The patterns a regex-compiled and stored in the class, to optimize performance.
        Look at self.relevance_test_list

        Currently supports:
        - OGC WxS services (WMS, WFS, WCS, WMTS, CSW)
        -
        TODO:
        - OGCAPI feature
        - REST services
        """
        return super().is_relevant(request_path, query_string)

    def collect_information(self, request_path: str, params: dict[str, Any]) -> dict:
        """
        Collect the app-specific information and structure it in a dict.
        Takes as input an already split URL: path and params
        :param request_path:
        :param params: a dict containing the request parameters
        :return: the same dict, with updated content (some lements can be removed)
        """
        infos = super().collect_information(request_path, params)
        if not infos:
            return None
        infos["workspaces"] = self.get_endpoint_from_path(request_path)
        return infos

    @staticmethod
    def get_endpoint_from_path(request_path: str) -> str:
        """
        In Mapproxy, the endpoint is always in the path. It is expected to be the last item in the path.
        To allow for aggregation between OGC servers, it will be called "workspace" in the DB anyway.
        """
        # Integrated GWC paths
        regex = r"(.*)/(service|ows|wms|wmts)"
        matches = re.search(regex, request_path)
        if matches:
            return matches[1]
        return ""
