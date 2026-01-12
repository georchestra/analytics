from georchestra_analytics_cli.access_logs.app_processors.mapserver import MapserverLogProcessor


def test_is_relevant():
    lp = MapserverLogProcessor(app_path="")
    assert lp.is_relevant("/administratif", "SERVICE=WFS&VERSION=1.1.0&REQUEST=GetCapabilities") == True
    assert lp.is_relevant("/ortho", "transparent=True&layers=ortho_2022&format=image/png&bbox=790678.4431818479,6543020.723557551,790893.4171401801,6543235.6975158835&width=1300&height=1300&srs=EPSG:2154&request=GetMap&version=1.1.1&service=WMS&styles=") == True
    assert lp.is_relevant("/geoserver/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage",
                          "1&filter=false&filter=false") == False


def test_collect_information():
    lp = MapserverLogProcessor(config={
        "infer_is_tiled": True
    })
    req_path = "/ortho"
    url_params = {'bbox': '795123.443181826,6545984.05689087,795338.4171401582,6546199.030849202', 'format': 'image/png', 'height': '1300', 'layers': 'ortho_2022', 'request': 'GetMap', 'service': 'WMS', 'srs': 'EPSG:2154', 'styles': '', 'transparent': 'True', 'version': '1.1.1', 'width': '1300'}

    assert lp.collect_information(req_path, url_params) == {
        'bbox': '795123.443181826,6545984.05689087,795338.4171401582,6546199.030849202',
        'format': 'image/png', "workspaces": "/ortho", 'layers': 'ortho_2022', 'crs': 'EPSG:2154', 'request': 'getmap',
        'service': 'WMS', 'size': '1300x1300', 'version': '1.1.1', 'width':'1300', 'height': '1300', 'styles': '', 'transparent': 'True', 'tags': ['ogc']}

def test_collect_information_is_tiled():
    lp = MapserverLogProcessor(config={
        "infer_is_tiled": True
    })
    req_path = "/ortho"
    url_params = {'bbox': '795123.443181826,6545984.05689087,795338.4171401582,6546199.030849202', 'format': 'image/png', 'height': '512', 'layers': 'ortho_2022', 'request': 'GetMap', 'service': 'WMS', 'srs': 'EPSG:2154', 'styles': '', 'transparent': 'True', 'version': '1.1.1', 'width': '512'}
    assert lp.collect_information(req_path, url_params) == {
        'bbox': '795123.443181826,6545984.05689087,795338.4171401582,6546199.030849202',
        'format': 'image/png', "workspaces": "/ortho", 'layers': 'ortho_2022', 'crs': 'EPSG:2154', 'request': 'getmap',
        'service': 'WMS', 'size': '512x512', 'version': '1.1.1', 'width':'512', 'height': '512', 'styles': '', 'transparent': 'True', "tiled": True, 'tags': ['ogc']}

def test_collect_information_is_download():
    lp = MapserverLogProcessor(config={
        "infer_is_tiled": True,
        'infer_is_download': True,
        'download_formats': {
            'vector': {'application/json': 'JSON', 'csv': 'CSV', 'excel': 'Excel', 'excel2007': "Excel",
                       'shape-zip': 'Shapefile'}
        }
    })
    req_path = "/administratif"
    url_params = "typeName=administratif:region&version=1.1.0&service=WFS&request=GetFeature&outputFormat=application/json&srsname=EPSG:3857"
    params = lp.collect_information_from_url(req_path+"?"+url_params)
    assert lp._infer_is_download(req_path, params) == (True, "JSON")


    url_params = {'download_format': 'JSON', 'is_download': True, 'layers': 'administratif:departement', 'outputformat': 'excel2007', 'request': 'getfeature', 'service': 'WFS', 'srsname': 'epsg:3857', 'version': '1.1.0', 'workspaces': '/administratif'}
    assert lp._infer_is_download(req_path, url_params) == (True, 'Excel')
    assert lp.collect_information(req_path, url_params).get('download_format') == 'Excel'
