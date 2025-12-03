"""
Process log files for the geoserver app
"""

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from georchestra_analytics_cli.utils import split_query_string
from georchestra_analytics_cli.access_logs.app_processors.abstract import AbstractLogProcessor


class GeoserverLogProcessor(AbstractLogProcessor):
    app_path: str = "geoserver"
    config: dict[str:Any] = {}

    def __init__(self, app_path: str = "geoserver", config: dict[str:Any] = {}):
        self.app_path = app_path
        self.config = config

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
        :return: the same dict, with updated content (some lements can be removed)
        """
        infos = {}
        try:
            for k, v in params.items():
                match k.lower():
                    case "layers":
                        infos["layers"] = _normalize_layers(request_path, v)
                    case "typename": # WFS GetFeature layers list
                        infos["layers"] = _normalize_layers(request_path, v)
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
                            if self.config.get("infer_is_tiled", False) and (infos["size"] in ["256x256", "512x512"]):
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
            if self.config.get("infer_is_download", False) is True:
                is_download, output_format = self._infer_is_download(request_path, params)
                if is_download:
                    infos["is_download"] = True
                    infos["download_format"] = output_format
            return infos
        except KeyError as e:
            logging.error(f"Key {e} not found in dictionary {params.__str__()}")
            return None

    def is_relevant(self, request_path: str, query_string: str) -> bool:
        # TODO: support REST & OGCAPI
        # This one should cover OGC Wxx requests
        return "service=" in query_string.lower()

    def _infer_is_download(self, request_path: str, url_params: dict[str, Any]) -> (bool, format):
        """
        Infer if the request is a download request. If yes, return also the format. Performs a mapping
        with the list of formats provided in the config file: allows both a filtering on the formats and
        more human-friendly names for the formats.

        """
        # TODO: support OGCAPI
        # Vector data:
        if url_params.get("service", "").lower() == "wfs" and url_params.get("request", "").lower() == "getfeature":
            req_format = url_params.get("outputformat", "").lower()
            download_formats = self.config.get("download_formats", {}).get("vector", {})
            if req_format in download_formats.keys():
                return True, download_formats.get(req_format)
        # Raster data:
        if url_params.get("service", "").lower() == "wcs" and url_params.get("request", "").lower() == "getcoverage":
            req_format = url_params.get("outputformat", "").lower()
            return True, req_format
        return False, None


def _append_workspace_if_missing(request_path: str, layername: str) -> str:
    """
    The workspace can be
    - provided in the layer name as a prefix
    - provided in the request path through the "Virtual Services"
    - both
    This function normalizes the layer name by prefixing it with the workspace if needed.
    """
    if ":" in layername:
        return layername
    else:
        regex = r"\/[a-zA-Z0-9-_]*\/(.*)\/(ows|wms|wfs|wcs|wmts)"
        try:
            matches = re.search(regex, request_path)
            return f"{matches[1]}:{layername}"
        except:
            logging.debug(f"Could not extract geoserver workspace name from path {request_path}")
            return layername


def _normalize_layers(request_path: str, layerparam: str) -> str:
    """
    Extract the layer name from the possible syntaxes allowed by OGC.
    Supports the eventuality of a request asking for several layers at once.
    Returns a string, a comma separated list of layers if there are several.
    (not a list because it will be complicated to handle once in the database,
    due to some limitations on the timescaledb continuous aggregates)
    """
    layers = [_append_workspace_if_missing(request_path.lower(), l.lower()) for l in layerparam.split(",")]
    return ",".join(layers)  # comma separated list of layers if there are several


