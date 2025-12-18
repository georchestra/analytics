
from typing import Any
from urllib.parse import parse_qs, urlparse

from prometheus_client import push_to_gateway, write_to_textfile


def int_or_none(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def float_or_none(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def dict_recursive_update(d, u):
    """
    Classic dict.update is not recursive.
    """
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = dict_recursive_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def split_url(url: str)-> tuple[str,str,str,str]:
    """
    U
    """
    url_parts = urlparse(url.lower())
    return url_parts.hostname, url_parts.path, url_parts.query, url_parts.fragment

def split_query_string(qs: str) -> dict[str, Any]:
    params = parse_qs(qs)

    # Flatten the dict (URL params supports repeated values which leads to values as list
    try:
        params = {k.lower(): v[0].lower() for k, v in params.items()}
    except KeyError as e:
        raise KeyError(f"Error when parsing query string {qs}")
    return params


def generate_app_id(keys: list[str]) -> str:
    """
    We want to make an identifier that would be unique accross several scenarii, like
    - different geoserver instances running on the same host, with paths that differ
    - different geoserver instances running on different hosts, with paths that might not differ
    A combination of server host and app path should be enough.
    If possible, it should fallback to the old, basic identifier being the app path (sufficient in simple cases like
    a single geOrchestra deployment, no external apps)
    """
    return "".join([k for k in keys if k is not None])


def write_prometheus_metrics(registry, metrics_filepath, pushgateway_url):
    if pushgateway_url:
        push_to_gateway(pushgateway_url, job='analytics-cli', registry=registry)
    if metrics_filepath:
        write_to_textfile(metrics_filepath, registry)
