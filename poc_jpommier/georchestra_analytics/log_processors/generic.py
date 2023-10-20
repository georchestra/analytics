"""
Generic log processor. Serves for simple cases or as fallback on apps for which a log processor has not yet been created
"""

import logging
from urllib.parse import urlparse, parse_qs

from .abstract import AbstractLogProcessor


class GenericLogProcessor(AbstractLogProcessor):
    @staticmethod
    def collect_information(url: str) -> dict:
        """Split request parameters into dict entries"""
        url_parts = urlparse(url.lower())
        url_params = parse_qs(url_parts.query)
        infos = {}
        try:
            for k,v in url_params.items():
                infos[k] = v[0]
        except Exception as e:
            logging.warning(f"Generic log processor could not parse url {url}. Error is {e}")
        return infos


    @staticmethod
    def is_relevant(path: str) -> bool:
        """ We cannot define a generic validation logic => keep all !"""
        return True