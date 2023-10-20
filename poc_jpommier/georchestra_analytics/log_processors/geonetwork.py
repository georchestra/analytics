"""\
Process log files for the geonetwork app
"""
import logging
import re
from urllib.parse import urlparse, parse_qs

from .utils import path_from_url
from .abstract import AbstractLogProcessor

valid_regexps = [
    ".*#\/metadata\/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(.*)",
    ".*\/api\/records\/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(.*)",
]


class GeonetworkLogProcessor(AbstractLogProcessor):
    @staticmethod
    def collect_information(url: str) -> dict:

        url_parts = urlparse(url.lower())
        url_params = parse_qs(url_parts.query)
        infos = {
            "query_type": "metadata_view",
            "uuid": get_metadata_uuid(url_parts.path),
        }
        return infos

    @staticmethod
    def is_relevant(path: str) -> bool:
        # keep = False
        # for pattern in valid_regexps:
        #     m = re.match(pattern, path)
        #     keep = (m is not None)
        keep = any(re.match(pattern, path) is not None for pattern in valid_regexps)
        return keep


def get_metadata_uuid(path: str) -> str:
    """Extract metadata uuid from URL"""
    for pattern in valid_regexps:
        m = re.match(pattern, path)
        if m is not None:
            return m[1]

    return None