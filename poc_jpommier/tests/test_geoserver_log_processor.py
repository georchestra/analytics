import unittest

from georchestra_analytics.log_processors import geoserver


class TestIsRelevant(unittest.TestCase):
    def test_gui_call_is_not_relevant(self):
        url = "http://geoserver:8080/geoserver/openlayers3/ol.js"
        log_processor = geoserver.GeoserverLogProcessor()
        self.assertFalse(log_processor.is_relevant(url))

    def test_WMS_call_is_relevant(self):
        url = "http://geoserver:8080/geoserver/sf/wms?SERVICE=WMS&VERSION=1.1.1&" \
                  "REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&STYLES&LAYERS=sf%3Abugsites&" \
                  "exceptions=application%2Fvnd.ogc.se_inimage&SRS=EPSG%3A26713&" \
                  "WIDTH=769&HEIGHT=330&BBOX=584699.4877203977%2C4911002.31779364%2C614018.4487134289%2C4923600.308845333"
        log_processor = geoserver.GeoserverLogProcessor()
        self.assertTrue(log_processor.is_relevant(url))

    def test_WMS_anonymous_call_is_relevant(self):
        url = "http://geoserver:8080/geoserver/topp/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image%2Fpng&" \
                  "TRANSPARENT=true&tiled=true&STYLES&LAYERS=topp%3Astates&exceptions=application%2Fvnd.ogc.se_inimage&" \
                  "tilesOrigin=-124.73142200000001%2C24.955967&WIDTH=256&HEIGHT=256&" \
                  "SRS=EPSG%3A4326&BBOX=-93.515625%2C44.6484375%2C-93.1640625%2C45"
        log_processor = geoserver.GeoserverLogProcessor()
        self.assertTrue(log_processor.is_relevant(url))


class TestGetWorkspace(unittest.TestCase):
    def test_get_from_layername(self):
        path = "/geoserver/sf/wfs"
        layerparam = "sf:whatever"
        self.assertEqual(geoserver.get_workspace_from_path_or_layerparam(path, layerparam), "sf")

    def test_get_from_path(self):
        path = "/geoserver/sf/wfs"
        layerparam = "whatever"  # It can happen that the name is in the path only
        self.assertEqual(geoserver.get_workspace_from_path_or_layerparam(path, layerparam), "sf")

    def test_get_multiple_from_layername(self):
        """ There can be several layers"""
        path = "/geoserver/wfs"
        layerparam = "sf:whatever,topp:states"
        self.assertEqual(geoserver.get_workspaces(path, layerparam), "sf,topp")

    def test_get_multiple_from_path(self):
        """ There can be several layers"""
        path = "/geoserver/sf/wfs"
        layerparam = "whatever,states"
        self.assertEqual(geoserver.get_workspaces(path, layerparam), "sf,sf")


class TestGetLayers(unittest.TestCase):
    def test_get_single_layer(self):
        layerparam = "sf:states"
        self.assertEqual(geoserver.get_layers(layerparam), "states")

    def test_get_multiple_layer(self):
        layerparam = "sf:whatever,topp:states"
        self.assertEqual(geoserver.get_layers(layerparam), "whatever,states")


class TestCollectInformation(unittest.TestCase):
    def test_collect_simple_wms(self):
        url = "http://geoserver:8080/geoserver/sf/wms?service=WMS&version=1.1.0&" \
              "request=GetMap&layers=sf%3Abugsites&" \
              "bbox=590223.4382724703%2C4914107.882513998%2C608462.4604629107%2C4920523.89081033" \
              "&width=768&height=330&srs=EPSG%3A26713&styles=&format=application/openlayers"
        expected_infos = {
            "service": "wms",
            "request": "getmap",
            "format": "application/openlayers",
            "workspace": "sf",
            "layers": "bugsites",
            "projection": "EPSG:26713",
            "version": "1.1.0",
            "size": "768x330",
            # "tiled": "false",
            "bbox": "590223.4382724703,4914107.882513998,608462.4604629107,4920523.89081033"
        }
        log_processor = geoserver.GeoserverLogProcessor()
        generated_infos = log_processor.collect_information(url)
        self.assertEqual(log_processor.collect_information(url), expected_infos)


if __name__ == '__main__':
    unittest.main()
