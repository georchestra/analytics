from georchestra_analytics_cli.access_logs.app_processors.dataapi import DataapiLogProcessor

class TestDataapiLogProcessor:
    config = {
        "download_formats": {
            "vector": {
                "shapefile": "Shapefile",
                "json": "JSON",
                "geojson": "GeoJSON",
                "csv": "CSV",
                "ooxml": "Excel",
            }
        }
    }
    lp = DataapiLogProcessor(config=config)

    def test_dataapi_log_processor_is_relevant(self):
        assert self.lp.is_relevant("/data/ogcapi/collections/psc:cours_eau", "limit=-1") == True
        assert self.lp.is_relevant("/data/ogcapi/collections/psc:cours_eau", "limit=50&f=ooxml") == True
        assert self.lp.is_relevant("/data/swagger-ui/index.html", "") == False

    def test_dataapi_log_processor_collect_information_simple(self):
        req_path = "/data/ogcapi/collections/psc:cours_eau"
        url_params = {}

        assert self.lp.collect_information(req_path, url_params) == {
            'layers': 'psc:cours_eau',
            }

    def test_dataapi_log_processor_collect_information_default_format(self):
        req_path = "/data/ogcapi/collections/psc:cours_eau/items"
        url_params = {'limit': '-1'}

        assert self.lp.collect_information(req_path, url_params) == {
            'layers': 'psc:cours_eau',
            'is_download': True,
            'download_format': 'GeoJSON',
            'full_download': True,
            'limit': '-1',
            'request': 'items'
        }

    def test_dataapi_log_processor_collect_information_from_url(self):
        assert self.lp.collect_information_from_url("/data/ogcapi/collections/psc:cours_eau/items?f=csv&limit=50") == {
            'layers': 'psc:cours_eau',
            'is_download': True,
            'download_format': 'CSV',
            'full_download': False,
            'limit': '50',
            'request': 'items'
        }

