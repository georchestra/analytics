"""
Process log files for the Geoserver app
Inherits from the generic OGC server processor
"""

import logging
import re
from typing import Any

from georchestra_analytics_cli.access_logs.app_processors.ogcserver import OgcserverLogProcessor


class GeoserverLogProcessor(OgcserverLogProcessor):
    app_path: str = "geoserver"

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

        if infos.get("layers", ""):
            workspaces, layers = self.normalize_layers(request_path, infos.get("layers"))
            infos["layers"] = ",".join(layers)
            infos["workspaces"] = ",".join(workspaces)
        return infos

    def normalize_layers(self, request_path, layerparam) -> tuple[list[str], list[str]]:
        """
        The workspace can be
        - provided in the layer name as a prefix
        - provided in the request path through the "Virtual Services"
        - both
        Knowing that there can be a list of layers with a mixed behaviour
        This function separates workspaces from layers

        return: tuple (workspaces, layers) each being a list of names since multiple layers can be provided
        """
        workspaces = []
        layers = []
        if not layerparam:
            return [],[]
        path_based_ws = self.get_workspace_from_path(request_path)
        for layer in layerparam.split(","):
            if ":" in layer:
                w, l = layer.split(":")
                workspaces.append(w)
                layers.append(l)
            else:
                workspaces.append(path_based_ws)
                layers.append(layer)
        # if we have several layers, but they use all the same workspace, we can squash it into a single entry
        if len(workspaces) > 1 and len(set(workspaces)) == 1:
            workspaces = [workspaces[0]]

        return workspaces, layers


    def get_workspace_from_path(self, request_path: str) -> str:
        """
        In Geoserver, the workspace can be provided in the path or in the query string as part of the layers parameter.
        There can even be a mix of both, for instance when requiring several layers, the ons without prefix will be
        taken on the path-based workspace, while others will tell explicitly which ws to look into.
        This function tries to extract the workspace from the path.
        """
        path = self.get_path_without_app_path(request_path)
        # Integrated GWC paths
        regexes = [
            r".*\/(.*)\/gwc\/service\/(ows|wms|wfs|wcs|wmts)",  # GWC paths
            r".*\/(.*)\/(ows|wms|wfs|wcs|wmts)",                # basic paths
        ]
        for regex in regexes:
            matches = re.search(regex, path)
            if matches:
                return matches[1]
        return ""
