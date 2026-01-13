import os

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

