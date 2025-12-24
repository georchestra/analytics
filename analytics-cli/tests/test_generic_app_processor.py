import os

from georchestra_analytics_cli.access_logs.app_processors.generic import GenericLogProcessor
from georchestra_analytics_cli.access_logs.app_processors.ogcserver import OgcserverLogProcessor
from georchestra_analytics_cli.config import load_config_from

config_file = os.path.join(os.path.dirname(__file__), "config_files/config_apps_processors.yaml")

def test_path_without_app_path():
    lp = GenericLogProcessor(app_path="gen")
    assert isinstance(lp, GenericLogProcessor)

def test_collect_information_from_url():
    lp = GenericLogProcessor(app_path="gen")
    assert lp.collect_information_from_url("https://demo.georchestra.org/gen/wms?service=wms&SERVICE=WMS&VERSION=1.3.0"
              "&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=base:roads&STYLES=base:roads&CRS=EPSG%3A3857"
              "&WIDTH=2304&HEIGHT=1084"
              "&BBOX=715133.0164035556%2C6042414.756063141%2C1074822.6263080558%2C6211643.721834183") == {}

def test_collect_information():
    lp = GenericLogProcessor(app_path="gen")
    req_path = "/gen/wms"
    url_params = {'bbox': '590223.4382724703,4914107.882513998,608462.4604629107,4920523.89081033',
                  'format': 'application/openlayers', 'height': '330', 'layers': 'sf:bugsites', 'request': 'getmap',
                  'service': 'wms', 'srs': 'epsg:26713', 'version': '1.1.0', 'width': '768'}

    assert lp.collect_information(req_path, url_params) == {}

def test_is_relevant():
    lp = GenericLogProcessor(app_path="gen")
    assert lp.is_relevant("/gen/wms", "service=wms&SERVICE=WMS&VERSION=1.3.0"
              "&REQUEST=GetCapbilities") == True