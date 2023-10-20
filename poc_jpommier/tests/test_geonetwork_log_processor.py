import unittest
from urllib.parse import urlparse

from georchestra_analytics.log_processors import geonetwork


class TestIsRelevant(unittest.TestCase):
    def test_gui_call_is_not_relevant(self):
        url = "http://geonetwork:8080/geonetwork/srv/eng/catalog.search"
        log_processor = geonetwork.GeonetworkLogProcessor()
        self.assertFalse(log_processor.is_relevant(url))

    def test_apirecords_call_is_relevant(self):
        url = "http://localhost:80/geonetwork/srv/api/records/da165110-88fd-11da-a88f-000d939bc5d8"
        log_processor = geonetwork.GeonetworkLogProcessor()
        self.assertTrue(log_processor.is_relevant(url))


class TestGetMetadataUuid(unittest.TestCase):
    def test_get_api_records_uuid(self):
        url = "http://localhost:80/geonetwork/srv/api/records/da165110-88fd-11da-a88f-000d939bc5d8"
        p = urlparse(url.lower()).path
        self.assertEqual(geonetwork.get_metadata_uuid(p), "da165110-88fd-11da-a88f-000d939bc5d8")


if __name__ == '__main__':
    unittest.main()
