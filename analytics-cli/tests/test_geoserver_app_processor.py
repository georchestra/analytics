from georchestra_analytics_cli.access_logs.app_processors.geoserver import GeoserverLogProcessor


def test_is_relevant():
    lp = GeoserverLogProcessor(app_path="geoserver")
    assert lp.is_relevant("/geoserver/ows", "service=WMS&version=1.3.0&request=GetCapabilities") == True
    assert lp.is_relevant("/geoserver/ows", "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=ortho_2022&STYLES=&WIDTH=256&HEIGHT=256&FORMAT=image%2Fjpeg&CRS=epsg%3A2154&DPI=120&MAP_RESOLUTION=120&FORMAT_OPTIONS=dpi%3A120&BBOX=702412.7441964962054044,6530023.647904840297997,702450.04307201399933547,6530060.94678035750985146") == True
    assert lp.is_relevant("/geoserver/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage",
                          "1&filter=false&filter=false") == False

def test_get_workspace_from_path():
    lp = GeoserverLogProcessor()
    assert lp.get_workspace_from_path('/geoserver/my_ws/ows') == 'my_ws'
    assert lp.get_workspace_from_path('/geoserver/ows') == ''
    assert lp.get_workspace_from_path('/geoserver/my_ws/gwc/service/wmts') == 'my_ws'
    assert lp.get_workspace_from_path('/geoserver/my_ws/service') == ''


def test_normalize_layers():
    lp = GeoserverLogProcessor()
    assert lp.normalize_layers('/geoserver/my_ws/ows', 'my_ws:dummy_layer') == (["my_ws"], ["dummy_layer"])
    assert lp.normalize_layers('/geoserver/my_ws/ows', 'dummy_layer1,dummy_layer2') == (["my_ws"], ["dummy_layer1", "dummy_layer2"])
    assert lp.normalize_layers('/geoserver/my_ws/ows', 'dummy_layer1,my_ws:dummy_layer2') == (["my_ws"], ["dummy_layer1", "dummy_layer2"])
    assert lp.normalize_layers('/geoserver/my_ws/ows', 'dummy_layer1,other_ws:dummy_layer2') == (["my_ws", "other_ws"], ["dummy_layer1", "dummy_layer2"])
    assert lp.normalize_layers('/geoserver/ows', 'my_ws:dummy_layer1,other_ws:dummy_layer2') == (["my_ws", "other_ws"], ["dummy_layer1", "dummy_layer2"])


def test_geoserver_log_processor():
    lp = GeoserverLogProcessor(config={
        "infer_is_tiled": True
    })
    req_path = "/geoserver/wms"
    url_params = {'bbox': '590223.4382724703,4914107.882513998,608462.4604629107,4920523.89081033',
                  'format': 'application/openlayers', 'height': '330', 'layers': 'sf:bugsites', 'request': 'getmap',
                  'service': 'wms', 'srs': 'epsg:26713', 'version': '1.1.0', 'width': '768'}

    assert lp.collect_information(req_path, url_params) == {
        'bbox': '590223.4382724703,4914107.882513998,608462.4604629107,4920523.89081033',
        'format': 'application/openlayers', "workspaces": "sf", 'layers': 'bugsites', 'crs': 'EPSG:26713', 'request': 'getmap',
        'service': 'WMS', 'size': '768x330', 'version': '1.1.0', 'width':'768', 'height': '330'}

    req_path = "/geoserver/sf/wms"
    url_params = {'format': 'image/png', 'height': '256', 'layers': 'bugsites,protected_areas', 'request': 'getmap',
                  'service': 'wms', 'srs': 'epsg:26713', 'version': '1.3.0', 'width': '256'}

    assert lp.collect_information(req_path, url_params) == {
        'format': 'image/png', "workspaces": "sf", 'layers': 'bugsites,protected_areas', 'crs': 'EPSG:26713',
        'request': 'getmap',
        'service': 'WMS', 'size': '256x256', 'version': '1.3.0', 'tiled': True, 'width':'256', 'height': '256'}

    assert lp.collect_information_from_url(
        "/geoserver/topp/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&tiled=true&STYLES&LAYERS=topp%3Astates&exceptions=application%2Fvnd.ogc.se_inimage&tilesOrigin=-124.73142200000001%2C24.955967&WIDTH=256&HEIGHT=256&SRS=EPSG%3A4326&BBOX=-92.4609375%2C44.6484375%2C-92.109375%2C45") == {
               'bbox': '-92.4609375,44.6484375,-92.109375,45',
               'exceptions': 'application/vnd.ogc.se_inimage',
               'format': 'image/png',
                "workspaces": "topp",
               'layers': 'states',
               'crs': 'EPSG:4326',
               'request': 'getmap',
               'service': 'WMS',
               'size': '256x256',
               'width': '256',
               'height': '256',
               'tiled': True,
               'tilesorigin': '-124.73142200000001,24.955967',
               'transparent': 'true',
               'version': '1.1.1'}

def test_geoserver_log_processor_is_download():
    lp = GeoserverLogProcessor(config={
        "infer_is_tiled": True,
        'infer_is_download': True,
        'download_formats': {
            'vector': {'application/json': 'JSON', 'csv': 'CSV', 'excel': 'Excel', 'excel2007': "Excel",
                       'shape-zip': 'Shapefile'}
        }
    })
    req_path = "/geoserver/topp/wfs"
    url_params = {'service': 'wfs', 'version': '1.1.0', 'request': 'getfeature', 'typename': 'topp:states'}
    assert lp._infer_is_download(req_path, url_params)[0] == False


    url_params = {'service': 'WFS', 'version': '1.1.0', 'request': 'GetFeature', 'typename': 'topp:states', 'outputformat': 'excel'}
    assert lp._infer_is_download(req_path, url_params) == (True, 'Excel')
    assert lp.collect_information(req_path, url_params).get('download_format') == 'Excel'
