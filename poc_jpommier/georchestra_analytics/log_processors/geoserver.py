"""\
Process log files for the geoserver app
"""
from apachelogs import LogParser, LogEntry
import logging
import re
from urllib.parse import urlparse, parse_qs

from . import path_from_url


def collect_information(url: str):
    url_parts = urlparse(url.lower())
    url_params = parse_qs(url_parts.query)
    try:
        infos = {
            "service": url_params["service"][0],
            "request": url_params["request"][0],
            "format": url_params["format"][0],
            "workspace": get_workspaces(url_parts.path, url_params["layers"][0]),
            "layers": get_layers(url_params["layers"][0]),
            "projection": url_params["srs"][0].upper(),
            "size": f"{url_params['width'][0]}x{url_params['height'][0]}",
            "tiled": url_params.get("tiled", ["false"])[0],
            "bbox": url_params['bbox'][0],
        }
        return infos
    except KeyError as e:
        logging.error(f"Key {e} not found in dictionary {url_params.__str__()}")
        return None


def is_relevant(url: str):
    path = path_from_url(url)
    return "service=" in path.lower()


def get_workspace_from_path_or_layerparam(path: str, layerparam: str) -> str:
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


def get_layers(layerparam: str) -> str:
    """ Extract the layer name from the possible syntaxes allowed by OGC. Needs to consider the
    eventuality of a request asking for several layers at once
    """
    layers = (l.split(":")[-1] for l in layerparam.split(","))
    return ",".join(layers) # comma separated list of layers if there are several


def get_workspaces(path: str, layerparam: str) -> str:
    """ Extract the workspace name from the possible syntaxes allowed by OGC. Needs to consider the
    eventuality of a request asking for several layers at once
    """
    workspaces = (get_workspace_from_path_or_layerparam(path, l) for l in layerparam.split(","))
    return ",".join(workspaces) # comma separated list of layers if there are several
