"""
Process log files for the mapstore app
NOT IMPLEMENTED YET

"""
import logging
import re
from urllib.parse import urlparse, parse_qs

from .abstract import AbstractLogProcessor


class MapstoreLogProcessor(AbstractLogProcessor):
    @staticmethod
    def collect_information(url: str) -> dict:
        url_parts = urlparse(url.lower())
        url_params = parse_qs(url_parts.query)
        infos = {}
        # try:
        #     for k,v in url_params.items():
        #         match k:
        #             case "layers":
        #                 infos["workspace"] = get_workspaces(url_parts.path, v[0])
        #                 infos["layers"] = _get_layers(v[0])
        #             case "height":
        #                 pass
        #             case "width":
        #                 if url_params.get("height", None):
        #                     infos["size"] = v[0] + "x" + url_params.get("height")[0]
        #             case "srs":
        #                 infos["projection"] = v[0].upper()
        #             case other:
        #                 infos[k] = v[0]
        #             # infos = {
        #             #     "service": get_value_or_none(url_params, "service"),
        #             #     "request": get_value_or_none(url_params, "request"),
        #             #     "format": get_value_or_none(url_params, "format"),
        #             #     "workspace": get_workspaces(url_parts.path, get_value_or_none(url_params, "layers")),
        #             #     "layers": get_layers(get_value_or_none(url_params, "layers")),
        #             #     "projection": get_value_or_none(url_params, "srs").upper(),
        #             #     "size": {get_value_or_none(url_params, "width")} + "x" + {get_value_or_none(url_params, "height")},
        #             #     "tiled": get_value_or_none(url_params, "tiled"),
        #             #     "bbox": get_value_or_none(url_params, 'bbox'),
        #             # }
        #     return infos
        # except KeyError as e:
        #     logging.error(f"Key {e} not found in dictionary {url_params.__str__()}")
        #     return None
        return None

    @staticmethod
    def is_relevant(path: str) -> bool:
        return False

