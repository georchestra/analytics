"""
Process log files for the Geoserver app
Inherits from the generic OGC server processor
"""

import logging
import re
from typing import Any
from urllib.parse import unquote, urlparse

from georchestra_analytics_cli.access_logs.app_processors.ogcserver import (
    OgcserverLogProcessor,
)


class GeoserverLogProcessor(OgcserverLogProcessor):
    app_path: str = "geoserver"

    # WMTS REST templates (ResourceURL syntax), configurable with the wmts_rest_templates key.
    # GeoServer (/gwc/service/wmts/rest/...) and standalone GeoWebCache (/geowebcache/service/wmts/rest/...)
    # Used by self.parse_wmts_rest_path()
    wmts_rest_templates = [
        "/service/wmts/rest/WMTSCapabilities.xml",
        "/service/wmts/rest/{Layer}/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}/{J}/{I}",
        "/service/wmts/rest/{Layer}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}/{J}/{I}",
        "/service/wmts/rest/{Layer}/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}",
        "/service/wmts/rest/{Layer}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}",
    ]
    # Regex used for each template variable. Default is a full path segment
    wmts_rest_variables_regex = {
        "tilerow": r"\d+",
        "tilecol": r"\d+",
        "i": r"\d+",
        "j": r"\d+",
        "style": r"[^/]*",  # GWC allows an empty style
    }

    def __init__(
        self, app_path: str = "", app_id: str = "", config: dict[str, Any] = {}
    ):
        super().__init__(app_path, app_id, config)
        templates = self.config.get("wmts_rest_templates", self.wmts_rest_templates)
        self.wmts_rest_patterns = [
            self.compile_wmts_rest_template(t) for t in (templates or [])
        ]

    @classmethod
    def compile_wmts_rest_template(cls, template: str) -> re.Pattern:
        """
        Convert a WMTS REST template (ResourceURL syntax) into a regex, with a named group for each variable.
        A full ResourceURL (with scheme, host and query string) is accepted: only its path is kept.
        """
        path = urlparse(template).path
        regex = ""
        pos = 0
        for m in re.finditer(r"\{([^{}/]+)\}", path):
            name = m[1].lower()
            variable_regex = cls.wmts_rest_variables_regex.get(name, r"[^/]+")
            regex += re.escape(path[pos : m.start()]) + f"(?P<{name}>{variable_regex})"
            pos = m.end()
        regex += re.escape(path[pos:])
        try:
            return re.compile(f"^.*{regex}/?$", re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Invalid WMTS REST template {template}: {e}")

    def parse_wmts_rest_path(self, request_path: str) -> dict[str, str]:
        """
        Parse a WMTS request using the RESTful encoding, where the parameters are provided in the path.
        Returns the parameters using the same names as the KVP encoding, so that they can be processed
        the same way. Returns an empty dict if the path doesn't match a supported WMTS REST template.
        """
        # Templates start with ^.*, so they match the full path, whether they include the app path or not
        for re_obj in self.wmts_rest_patterns:
            m = re_obj.match(request_path)
            if not m:
                continue
            params = {k: unquote(v) for k, v in m.groupdict().items() if v is not None}
            if "i" in params and "j" in params:
                request = "getfeatureinfo"
            elif "tilerow" in params or "tilecol" in params:
                request = "gettile"
            else:
                request = "getcapabilities"
            return {"service": "WMTS", "version": "1.0.0", "request": request, **params}
        return {}

    def is_relevant(self, request_path: str, query_string: str) -> bool:
        """
        Check if the request matches a pattern corresponding to a query we want to track.
        The patterns a regex-compiled and stored in the class, to optimize performance.
        Look at self.relevance_test_list

        Currently supports:
        - OGC WxS services (WMS, WFS, WCS, WMTS, CSW)
        - WMTS RESTful encoding
        -
        TODO:
        - OGCAPI feature
        - REST services
        """
        return super().is_relevant(request_path, query_string) or bool(
            self.parse_wmts_rest_path(request_path)
        )

    def collect_information(self, request_path: str, params: dict[str, Any]) -> dict:
        """
        Collect the app-specific information and structure it in a dict.
        Takes as input an already split URL: path and params
        :param request_path:
        :param params: a dict containing the request parameters
        :return: the same dict, with updated content (some lements can be removed)
        """
        # WMTS REST requests: the parameters are in the path. The query string params, if any, take precedence
        wmts_rest_params = self.parse_wmts_rest_path(request_path)
        if wmts_rest_params:
            params = {**wmts_rest_params, **params}
        infos = super().collect_information(request_path, params)
        if not infos:
            return None

        if infos.get("layers", ""):
            workspaces, layers = self.normalize_layers(
                request_path, infos.get("layers")
            )
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
            return [], []
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
        # GWC paths (KVP or REST, whatever the configured WMTS REST templates), optionally prefixed by a workspace.
        # Checked first, so that path segments after /gwc/ (e.g. "service" or "rest") are not taken as a workspace
        matches = re.search(r"^(?:/([^/]+))?/gwc(/|$)", path)
        if matches:
            return matches[1] or ""
        # Integrated GWC paths
        regexes = [
            r".*\/(.*)\/gwc\/service\/(ows|wms|wfs|wcs|wmts)",  # GWC paths
            r".*\/(.*)\/(ows|wms|wfs|wcs|wmts)",  # basic paths
            r".*collections\/([^/]*){1}",  # basic paths
        ]
        for regex in regexes:
            matches = re.search(regex, path)
            if matches:
                return matches[1]
        return ""
