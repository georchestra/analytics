"""
Process log files for the Data API app.
https://github.com/georchestra/data-api
"""

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from georchestra_analytics_cli.utils import split_query_string
from georchestra_analytics_cli.access_logs.app_processors.abstract import AbstractLogProcessor


class DataapiLogProcessor(AbstractLogProcessor):
    app_path: str = "data"
    config: dict[str:Any] = {}
    download_formats: dict[str:Any] = {}

    def __init__(self, app_path: str = "data", config: dict[str:Any] = {}):
        self.app_path = app_path
        self.config = config
        self.download_formats = self.config.get("download_formats", {}).get("vector", {})

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
            return {}

    def collect_information(self, request_path: str, params: dict[str, Any]) -> dict:
        """
        Collect the app-specific information and structure it in a dict.
        Takes as input an already split URL: path and params
        :param request_path:
        :param params: a dict containing the request parameters
        :return: the same dict, with updated content (some elements can be removed)
        """
        regex = r".*\/ogcapi\/collections\/(.*)"
        match = re.match(regex, request_path)
        if match is not None:
            # This should get the layer name and instructions.
            path_chunks = match[1].split("/")
            # Dataset name is the first chunk of the path
            dataset = path_chunks[0]
            params["layers"] = dataset

            if len(path_chunks) > 1:
                # Currently, the only supported instruction is "items"
                if path_chunks[1] == "items":
                    params["request"] = "items"
                    params["is_download"] = True

                    # Default format is GeoJSON
                    # Rename the f param (hence "pop")
                    params["download_format"] = self.download_formats.get(params.pop("f", "geojson"))

                    # Check if full download or paginated download
                    params["full_download"] = params.get("limit", None) == "-1"
        return params

    def is_relevant(self, request_path: str, query_string: str) -> bool:
        """
        Whether the log record should be processed or dropped.
        """
        regex = r".*\/ogcapi\/collections\/(.*)"
        relevant = re.match(regex, request_path)
        return relevant is not None
