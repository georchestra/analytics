import os

import pytest

from georchestra_analytics_cli.access_logs.app_processors.ogcserver import OgcserverLogProcessor
from georchestra_analytics_cli.config import load_config_from

config_file = os.path.join(os.path.dirname(__file__), "config_files/config_apps_processors.yaml")

def test_path_without_app_path():
    lp = OgcserverLogProcessor(app_path="geoserver")
    assert lp.get_path_without_app_path("/geoserver/ogc/features/v1") == "/ogc/features/v1"
    assert lp.get_path_without_app_path("/ortho/service") == "/ortho/service"

def test_get_path_without_app_path_with_root_path():
    lp = OgcserverLogProcessor(app_path="")
    assert lp.get_path_without_app_path("/orthos/service") == "/orthos/service"

def test_is_relevant():
    lp = OgcserverLogProcessor(app_path="geoserver")
    assert lp.is_relevant("/geoserver/ows", "service=WMS&version=1.3.0&request=GetCapabilities") == True
    assert lp.is_relevant("/geoserver/ows", "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=ortho_2022&STYLES=&WIDTH=256&HEIGHT=256&FORMAT=image%2Fjpeg&CRS=epsg%3A2154&DPI=120&MAP_RESOLUTION=120&FORMAT_OPTIONS=dpi%3A120&BBOX=702412.7441964962054044,6530023.647904840297997,702450.04307201399933547,6530060.94678035750985146") == True
    assert lp.is_relevant("/geoserver/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage",
                          "1&filter=false&filter=false") == False

def test_is_relevant_with_root_path():
    lp = OgcserverLogProcessor(app_path="")
    assert lp.is_relevant("/orthos", "service=WMS&version=1.3.0&request=GetCapabilities") == True
    assert lp.is_relevant("/","") == False

def test_is_download():
    conf = load_config_from(config_file)
    lp = OgcserverLogProcessor(app_path="ogc", config=conf.get_app_processors_config().get("ogcserver", {}))
    assert lp._infer_is_download("/ogc/ows",
                {"service": "WFS", "request": "getfeature", "outputformat": "excel"}) == (True, "Excel")
    assert lp._infer_is_download("/ogc/ows",
                {"service": "WCS", "request": "getcoverage", "format": "geotiff"}) == (True, "GeoTiff")
    assert lp._infer_is_download("/ogc/ows",
                {"service": "WMTS", "request": "getmap", "format": "geotiff"}) == (False, None)


def test_collect_information_from_url():
    conf = load_config_from(config_file)
    lp = OgcserverLogProcessor(app_path="ogc", config=conf.get_app_processors_config().get("ogcserver", {}))
    assert lp.collect_information_from_url("https://demo.georchestra.org/geoserver/wms?service=wms&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=base:roads&STYLES=base:roads&CRS=EPSG%3A3857&WIDTH=2304&HEIGHT=1084&BBOX=715133.0164035556%2C6042414.756063141%2C1074822.6263080558%2C6211643.721834183") == {
        "service": "WMS", "request": "getmap", "version": "1.3.0", "format": "image/png", "layers": "base:roads",
        'styles': 'base:roads', 'bbox': '715133.0164035556,6042414.756063141,1074822.6263080558,6211643.721834183',
        'crs': 'EPSG:3857', 'height': '1084', 'width': '2304', 'size': '2304x1084', 'transparent': 'true', 'tags': ['ogc']
    }

def test_collect_information_from_url_with_tiled():
    conf = load_config_from(config_file)
    lp = OgcserverLogProcessor(app_path="ogc", config=conf.get_app_processors_config().get("ogcserver", {}))
    assert lp.collect_information_from_url("https://demo.georchestra.org/geoserver/wms?service=wms&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=base:roads&STYLES=base:roads&CRS=EPSG%3A3857&WIDTH=256&HEIGHT=256&BBOX=312735.5839256644%2C5941976.09458765%2C625471.1678513302%2C6254711.678513316") == {
        "service": "WMS", "request": "getmap", "version": "1.3.0", "format": "image/png", "layers": "base:roads",
        'styles': 'base:roads', 'bbox': '312735.5839256644,5941976.09458765,625471.1678513302,6254711.678513316',
        'crs': 'EPSG:3857', 'height': '256', 'width': '256', 'size': '256x256', 'transparent': 'true', 'tiled': True, 'tags': ['ogc']
    }

def test_collect_information_plain():
    conf = load_config_from(config_file)
    lp = OgcserverLogProcessor(app_path="ogc", config=conf.get_app_processors_config().get("ogcserver", {}))
    assert lp.collect_information("/ogc/ows",
                                  {"service": "WMS", "version":"1.3.0", "request": "getMap", "FORMAT": "image%2Fpng", "layers": "ortho2025"}) == {
        "service": "WMS", "request": "getmap", "version": "1.3.0", "format": "image%2Fpng", "layers": "ortho2025", 'tags': ['ogc']
    }

def test_collect_information_with_download():
    conf = load_config_from(config_file)
    lp = OgcserverLogProcessor(app_path="ogc", config=conf.get_app_processors_config().get("ogcserver", {}))
    assert lp.collect_information("/ogc/ows",
                                  {"service": "WFS", "request": "getFeature", "outputFormat": "excel"}) == {
        "service": "WFS", "request": "getfeature", "outputformat": "excel", "download_format": "Excel", "is_download": True, 'tags': ['ogc']
    }


def test_parse_wmts_rest_path():
    lp = OgcserverLogProcessor(app_path="ogc")
    # GeoServer / GeoWebCache templates
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/wmtscapabilities.xml") == {
        "service": "WMTS", "version": "1.0.0", "request": "getcapabilities"
    }
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp%3astates/population/epsg%3a4326/epsg%3a4326%3a3/2/5") == {
        "service": "WMTS", "version": "1.0.0", "request": "gettile", "layer": "topp:states", "style": "population",
        "tilematrixset": "epsg:4326", "tilematrix": "epsg:4326:3", "tilerow": "2", "tilecol": "5"
    }
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp:states/epsg:4326/epsg:4326:3/2/5") == {
        "service": "WMTS", "version": "1.0.0", "request": "gettile", "layer": "topp:states",
        "tilematrixset": "epsg:4326", "tilematrix": "epsg:4326:3", "tilerow": "2", "tilecol": "5"
    }
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp:states/population/epsg:4326/epsg:4326:3/2/5/120/44") == {
        "service": "WMTS", "version": "1.0.0", "request": "getfeatureinfo", "layer": "topp:states", "style": "population",
        "tilematrixset": "epsg:4326", "tilematrix": "epsg:4326:3", "tilerow": "2", "tilecol": "5", "j": "120", "i": "44"
    }
    # Standalone GeoWebCache
    assert lp.parse_wmts_rest_path("/geowebcache/service/wmts/rest/raster:ortho2014/default/epsg:3857/epsg:3857:12/1435/2105") == {
        "service": "WMTS", "version": "1.0.0", "request": "gettile", "layer": "raster:ortho2014", "style": "default",
        "tilematrixset": "epsg:3857", "tilematrix": "epsg:3857:12", "tilerow": "1435", "tilecol": "2105"
    }
    # Not WMTS REST
    assert lp.parse_wmts_rest_path("/ogc/gwc/rest/wmts/topp:states/epsg:4326/epsg:4326:3/2/5") == {}  # GWC admin API
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts") == {}
    assert lp.parse_wmts_rest_path("/ogc/gwc/rest/layers") == {}

def test_is_relevant_wmts_rest():
    lp = OgcserverLogProcessor(app_path="ogc")
    assert lp.is_relevant("/ogc/gwc/service/wmts/rest/topp:states/epsg:4326/epsg:4326:3/2/5", "format=image/png") == True
    assert lp.is_relevant("/ogc/gwc/rest/layers", "") == False

def test_collect_information_wmts_rest():
    lp = OgcserverLogProcessor(app_path="ogc")
    assert lp.collect_information_from_url("/ogc/gwc/service/wmts/rest/topp:states/epsg:4326/EPSG:4326:3/2/5?format=image/png") == {
        "service": "WMTS", "version": "1.0.0", "request": "gettile", "layers": "topp:states", "format": "image/png",
        "tilematrixset": "epsg:4326", "tilematrix": "epsg:4326:3", "tilerow": "2", "tilecol": "5", "tags": ["ogc"]
    }

def test_compile_wmts_rest_template():
    regex = OgcserverLogProcessor.compile_wmts_rest_template(
        "https://example.org/geoserver/gwc/service/wmts/rest/ws:layer/{style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}?format=image/png")
    assert regex.match("/geoserver/gwc/service/wmts/rest/ws:layer/s/epsg:4326/epsg:4326:3/1/7").groupdict() == {
        "style": "s", "tilematrixset": "epsg:4326", "tilematrix": "epsg:4326:3", "tilerow": "1", "tilecol": "7"}
    # TileRow and TileCol must be integers
    assert regex.match("/geoserver/gwc/service/wmts/rest/ws:layer/s/epsg:4326/epsg:4326:3/a/7") is None
    with pytest.raises(ValueError):
        OgcserverLogProcessor.compile_wmts_rest_template("/wmts/{1layer}/{TileRow}/{TileCol}")
    with pytest.raises(ValueError):
        OgcserverLogProcessor.compile_wmts_rest_template("/wmts/{Layer}/{Layer}/{TileRow}/{TileCol}")

def test_wmts_rest_templates_from_config():
    lp = OgcserverLogProcessor(app_path="ogc", config={"wmts_rest_templates": [
        "/gwc/service/wmts/rest/WMTSCapabilities.xml",
        "/gwc/service/wmts/rest/{Layer}/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}",
        # Dimension in the path
        "/gwc/service/wmts/rest/{Layer}/{Style}/{TileMatrixSet}/{Time}/{TileMatrix}/{TileRow}/{TileCol}",
    ]})
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/wmtscapabilities.xml") == {
        "service": "WMTS", "version": "1.0.0", "request": "getcapabilities"}
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp:states/population/epsg:4326/epsg:4326:3/1/7") == {
        "service": "WMTS", "version": "1.0.0", "request": "gettile", "layer": "topp:states", "style": "population",
        "tilematrixset": "epsg:4326", "tilematrix": "epsg:4326:3", "tilerow": "1", "tilecol": "7"}
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp:states/population/epsg:4326/2020/epsg:4326:3/1/7") == {
        "service": "WMTS", "version": "1.0.0", "request": "gettile", "layer": "topp:states", "style": "population",
        "tilematrixset": "epsg:4326", "time": "2020", "tilematrix": "epsg:4326:3", "tilerow": "1", "tilecol": "7"}
    # The default templates are replaced, not extended: no template without style anymore
    assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp:states/epsg:4326/epsg:4326:3/1/7") == {}
    assert lp.is_relevant("/ogc/gwc/service/wmts/rest/topp:states/epsg:4326/epsg:4326:3/1/7", "") == False

def test_wmts_rest_templates_disabled_from_config():
    for templates in ([], None):
        lp = OgcserverLogProcessor(app_path="ogc", config={"wmts_rest_templates": templates})
        assert lp.parse_wmts_rest_path("/ogc/gwc/service/wmts/rest/topp:states/epsg:4326/epsg:4326:3/1/7") == {}

def test_ignored_status_codes():
    assert OgcserverLogProcessor().ignored_status_codes == [301, 302, 303, 307, 308]
    assert OgcserverLogProcessor(config={"ignored_status_codes": [404]}).ignored_status_codes == [404]
    assert OgcserverLogProcessor(config={"ignored_status_codes": None}).ignored_status_codes == []
