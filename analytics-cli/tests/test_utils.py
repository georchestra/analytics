from georchestra_analytics_cli.utils import *

def test_int_or_none():
    assert int_or_none("1") == 1
    assert int_or_none("will fail") is None

def test_dict_recursive_update():
    d1 = {"a": "orig", "b": {"c": 2}}
    d2 = {"a": "updt", "b": {"d": 3}, "e": 4}
    dict_recursive_update(d1, d2)
    assert d1 == {"a": "updt", "b": {"c": 2, "d": 3}, "e": 4}

def test_split_url():
    assert split_url("https://www.geo2france.fr/geonetwork/srv/fre/catalog.search#/metadata/487d9e9a-6df5-4c93-b329-cd7c3141f678") == ("www.geo2france.fr", "/geonetwork/srv/fre/catalog.search", "", "/metadata/487d9e9a-6df5-4c93-b329-cd7c3141f678")
    assert split_url("/geoserver/ows?service=WMS&version=1.3.0&request=GetCapabilities") == (None, "/geoserver/ows", "service=WMS&version=1.3.0&request=GetCapabilities".lower(), "")

def test_split_query_string():
    assert split_query_string("service=WMS&version=1.3.0&request=GetCapabilities") == {"service": "wms", "version": "1.3.0", "request": "getcapabilities"}

def test_generate_app_id():
    assert generate_app_id(["www.geo2france.fr", "/geoserver/"]) == "www.geo2france.fr/geoserver/"
    assert generate_app_id(["/geoserver/"]) == "/geoserver/"
    assert generate_app_id(["www.craig.fr", "/"]) == "www.craig.fr/"