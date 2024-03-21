"""
Process log files for the geoserver app
"""
import logging
import re
from urllib.parse import urlparse, parse_qs

from .abstract import AbstractLogProcessor


class GeoserverLogProcessor(AbstractLogProcessor):
    @staticmethod
    def collect_information(url: str) -> dict:
        url_parts = urlparse(url.lower())
        url_params = parse_qs(url_parts.query)
        infos = {}
        try:
            for k,v in url_params.items():
                match k:
                    case "layers":
                        infos["workspace"] = get_workspaces(url_parts.path, v[0])
                        infos["layers"] = _get_layers(v[0])
                    case "height":
                        pass
                    case "width":
                        if url_params.get("height", None):
                            infos["size"] = v[0] + "x" + url_params.get("height")[0]
                    case "srs":
                        infos["projection"] = v[0].upper()
                    case other:
                        infos[k] = v[0]
                    # infos = {
                    #     "service": get_value_or_none(url_params, "service"),
                    #     "request": get_value_or_none(url_params, "request"),
                    #     "format": get_value_or_none(url_params, "format"),
                    #     "workspace": get_workspaces(url_parts.path, get_value_or_none(url_params, "layers")),
                    #     "layers": get_layers(get_value_or_none(url_params, "layers")),
                    #     "projection": get_value_or_none(url_params, "srs").upper(),
                    #     "size": {get_value_or_none(url_params, "width")} + "x" + {get_value_or_none(url_params, "height")},
                    #     "tiled": get_value_or_none(url_params, "tiled"),
                    #     "bbox": get_value_or_none(url_params, 'bbox'),
                    # }
            return infos
        except KeyError as e:
            logging.error(f"Key {e} not found in dictionary {url_params.__str__()}")
            return None

    @staticmethod
    def is_relevant(path: str) -> bool:
        return "service=" in path.lower()


def _get_workspace_from_path_or_layerparam(path: str, layerparam: str) -> str:
    """
    Geoserver allows to provide the workspace either in the layer name as a prefix or in the URl through
    "Virtual Services". We have to consider those 2 possibilities
    :param path:
    :param layerparam:
    :return:
    """
    layerparts = layerparam.split(":")
    if len(layerparts) > 1:
        return layerparts[0]
    else:
        regex = "\/[a-zA-Z0-9-_]*\/(.*)\/(ows|wms|wfs|wcs|wmts)"
        try:
            matches = re.search(regex, path)
            return matches[1]
        except:
            logging.warning(f'Could not extract geoserver workspace name from path {path}')
            return ''


def _get_layers(layerparam: str) -> str:
    """ Extract the layer name from the possible syntaxes allowed by OGC. Needs to consider the
    eventuality of a request asking for several layers at once
    """
    layers = (l.split(":")[-1] for l in layerparam.split(","))
    return ",".join(layers)  # comma separated list of layers if there are several


def get_workspaces(path: str, layerparam: str) -> str:
    """ Extract the workspace name from the possible syntaxes allowed by OGC. Needs to consider the
    eventuality of a request asking for several layers at once
    """
    workspaces = (_get_workspace_from_path_or_layerparam(path, l) for l in layerparam.split(","))
    return ",".join(workspaces)  # comma separated list of layers if there are several
