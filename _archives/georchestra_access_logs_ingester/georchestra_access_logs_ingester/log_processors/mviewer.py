"""
Process log files for the mviewer app
"""
import logging
import re
from urllib.parse import urlparse, parse_qs

from .abstract import AbstractLogProcessor


class MviewerLogProcessor(AbstractLogProcessor):
    @staticmethod
    def collect_information(url: str) -> dict:
        url_parts = urlparse(url.lower())
        url_params = parse_qs(url_parts.query)
        infos = {}
        try:
            for k,v in url_params.items():
                match k:
                    case "config":
                        # We get the map name (xml file path)
                        infos["map"] = v[0]
            return infos
        except KeyError as e:
            logging.error(f"Key {e} not found in dictionary {url_params.__str__()}")
            return None

    @staticmethod
    def is_relevant(path: str) -> bool:
        return "config=" in path.lower()


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
