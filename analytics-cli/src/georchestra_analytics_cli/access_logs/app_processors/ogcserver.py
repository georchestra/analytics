"""
Process log files for an OGC server (generic)
"""

import fnmatch
import logging
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from georchestra_analytics_cli.access_logs.app_processors.abstract import (
    AbstractLogProcessor,
)
from georchestra_analytics_cli.utils import split_query_string


class OgcserverLogProcessor(AbstractLogProcessor):
    app_path: str = "ogcserver"
    app_id: str = app_path
    config: dict[str, Any] = {}

    # List of regex patterns use to determine if a request is relevant for the usage analytics.
    # Used by self.is_relevant()
    relevance_test_list = [
        # OGC WxS services
        re.compile(r".*\?.*(service=).*", re.IGNORECASE),
        # OGCAPI services
        re.compile("^.*/collections/.+", re.IGNORECASE),
    ]

    # WMTS REST templates (ResourceURL syntax), configurable with the wmts_rest_templates key.
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

    # Redirections would be counted twice (the target request is logged too), configurable with the
    # ignored_status_codes key
    ignored_status_codes = [301, 302, 303, 307, 308]

    def __init__(
        self, app_path: str = "", app_id: str = "", config: dict[str, Any] = {}
    ):
        self.app_path = app_path if app_path else self.app_path
        self.app_id = app_id if app_id else self.app_path
        self.config = config
        self.ignored_status_codes = (
            self.config.get("ignored_status_codes", self.ignored_status_codes) or []
        )
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
        full_req = self.get_path_without_app_path(request_path) + "?" + query_string
        return any(
            re_obj.match(full_req) for re_obj in self.relevance_test_list
        ) or bool(self.parse_wmts_rest_path(request_path))

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

    def collect_information_from_url(self, url: str) -> dict:
        """
        Collect the app-specific information and structure it in a dict.
        :param url: the request url:
        :return: a dict with the app-specific information
        """
        # Lowercase the full URL to
        url_parts = urlparse(url.lower())

        # Flatten the dict (URL params supports repeated values which leads to values as list
        try:
            url_params = split_query_string(url_parts.query)
            return self.collect_information(url_parts.path, url_params)
        except KeyError as e:
            logging.error(e)
            return None

    def collect_information(self, request_path: str, params: dict[str, Any]) -> dict:
        """
        Collect the app-specific information and structure it in a dict.
        Takes as input an already split URL: path and params
        :param request_path:
        :param params: a dict containing the request parameters
        :return: the same dict, with updated content (some elements can be removed)
        """
        infos = {}
        # WMTS REST requests: the parameters are in the path. The query string params, if any, take precedence
        wmts_rest_params = self.parse_wmts_rest_path(request_path)
        if wmts_rest_params:
            params = {**wmts_rest_params, **params}
        try:
            for k, v in params.items():
                match k.lower():
                    # WMTS GetTile & WMS GetLegendGraphic parameter is layer=xxx
                    case "layer":
                        infos["layers"] = v
                    case "layers":
                        infos["layers"] = v
                    case "typename":  # WFS GetFeature layers list
                        infos["layers"] = v
                    case "typenames":
                        infos["layers"] = v
                    case "tiled":
                        # Make it a boolean
                        if isinstance(v, str):
                            infos["tiled"] = v.lower() in ["true"]
                        else:
                            infos["tiled"] = v
                    case "height":
                        infos["height"] = v
                    case "width":
                        infos["width"] = v
                        if params.get("height", None):
                            infos["size"] = v + "x" + params.get("height")
                            if self.config.get("infer_is_tiled", False) and (
                                infos["size"] in ["256x256", "512x512"]
                            ):
                                infos["tiled"] = True
                    case "srs":
                        # Unify to crs, which is the key used on WMS 1.3.0
                        infos["crs"] = v.upper()
                    case "crs":
                        infos["crs"] = v.upper()
                    case "service":
                        # Make it uppercase
                        infos["service"] = v.upper()
                    case "request":
                        # Make it lowercase
                        infos["request"] = v.lower()
                    case other:
                        infos[k.lower()] = v
            if self.is_ogc_api_features(request_path):
                self._infer_layer_from_url(request_path, infos)
            if self.config.get("infer_is_download", False) is True:
                is_download, output_format = self._infer_is_download(
                    request_path, infos
                )
                if is_download:
                    infos["is_download"] = True
                    infos["download_format"] = output_format

            # Tags will allow us to filter the records for the analysis views, e.g. OGC analytics
            infos["tags"] = ["ogc"]
            return infos
        except KeyError as e:
            logging.error(f"Key {e} not found in dictionary {params.__str__()}")
            return None

    def _infer_is_download(
        self, request_path: str, url_params: dict[str, Any]
    ) -> (bool, format):
        """
        Infer if the request is a download request. If yes, return also the format. Performs a mapping
        with the list of formats provided in the config file: allows both a filtering on the formats and
        more human-friendly names for the formats.

        """
        # Vector data:
        if (self.is_ogc_api_features(request_path)):
            req_format = url_params.get("f", "").lower()
            download_formats = self.config.get("download_formats", {}).get("vector", {})
            if req_format in download_formats.keys():
                return True, download_formats.get(req_format, req_format)
        if (
            url_params.get("service", "").lower() == "wfs"
            and url_params.get("request", "").lower() == "getfeature"
        ):
            req_format = url_params.get("outputformat", "").lower()
            download_formats = self.config.get("download_formats", {}).get("vector", {})
            if req_format in download_formats.keys():
                return True, download_formats.get(req_format, req_format)
        # Raster data:
        if (
            url_params.get("service", "").lower() == "wcs"
            and url_params.get("request", "").lower() == "getcoverage"
        ):
            req_format = url_params.get("format", "").lower()
            download_formats = self.config.get("download_formats", {}).get("raster", {})
            return True, download_formats.get(req_format, req_format)
        return False, None

    def get_path_without_app_path(self, request_path: str) -> str:
        """
        Remove the app path from the path.
        Useful to homogenize between cases when the app path is root (not likely with geOrchestra proxied apps,
        but more likely when collecting usage data from externally managed apps like mapserver)
        """
        if request_path.startswith(f"/{self.app_path}/"):
            request_path = request_path.replace(f"/{self.app_path}/", "/", 1)
        return request_path

    def is_ogc_api_features(self, request_path: str) -> bool:
        return request_path.__contains__("/ogc/features/")

    def _infer_layer_from_url(self, request_path: str, infos: dict[str, Any]) -> None:
        infos['service'] = "OGC API Features"
        m = re.compile("^.*/ogc/features/.*/collections/([^/]+){1}/?(items)?", re.IGNORECASE)
        res = m.search(request_path)
        if res:
            infos['layers'] = res.group(1)
            infos['request'] = 'items' if res.group(2) else 'layer'
