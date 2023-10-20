import unittest

import apachelogs

from georchestra_analytics.log_processors import core


class TestReadRequestLine(unittest.TestCase):
    def test_read_http_url(self):
        req = "GET /geonetwork/srv/fre/csw?service=CSW&version=2.0.2&request=GetRecords&constraintlanguage=CQL_TEXT&" \
              "typenames=gmd:MD_Metadata HTTP/1.1"
        expected_result = ("GET",
                           "/geonetwork/srv/fre/csw?service=CSW&version=2.0.2&request=GetRecords"
                           "&constraintlanguage=CQL_TEXT&typenames=gmd:MD_Metadata",
                           "geonetwork"
                           )
        self.assertEqual(core.read_request_line(req), expected_result)


    def test_read_path(self):
        req = "GET /geoserver/nurc/wms?service=WMS&version=1.1.0&request=GetMap&layers=nurc%3AArc_Sample" \
              "&bbox=-180.0%2C-90.0%2C180.0%2C90.0&width=768&height=384&srs=EPSG%3A4326&styles=" \
              "&format=application/openlayers HTTP/1.1"
        expected_result = ("GET",
                           "/geoserver/nurc/wms?service=WMS&version=1.1.0&request=GetMap&layers=nurc%3AArc_Sample" \
                           "&bbox=-180.0%2C-90.0%2C180.0%2C90.0&width=768&height=384&srs=EPSG%3A4326&styles=" \
                           "&format=application/openlayers",
                           "geoserver"
                           )
        self.assertEqual(core.read_request_line(req), expected_result)


class TestCollectCommonData(unittest.TestCase):
    """
    Collecting common data only
    """
    def test_read_logline(self):
        logformat = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" - \"%{app}n\" \"-\" %{ms}Tms"
        logline = '192.168.1.70 - testadmin|Project Steering Committee|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN,ROLE_USER,' \
                  'ROLE_ADMINISTRATOR,ROLE_GN_ADMIN,ROLE_EMAILPROXY [18/Oct/2023:17:36:06 +0000] ' \
                  '"GET /geoserver/nurc/wms?service=WMS&version=1.1.0&request=GetMap&layers=nurc%3AArc_Sample' \
                  '&bbox=-180.0%2C-90.0%2C180.0%2C90.0&width=768&height=384&srs=EPSG%3A4326&styles=' \
                  '&format=application/openlayers HTTP/1.1" 200 - "-" ' \
                  '"Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0" - "geoserver" "-" 18ms'
        logentry = apachelogs.parse_lines(logformat, [logline])
        data = core.collect_common_data(next(logentry))
        expected_data = {
            'timestamptz': '2023-10-18T17:36:06+00:00',
             'username': 'testadmin',
             'org': 'Project Steering Committee',
             'roles': 'ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN,ROLE_USER,ROLE_ADMINISTRATOR,ROLE_GN_ADMIN,ROLE_EMAILPROXY',
             'request_path': '/geoserver/nurc/wms?service=WMS&version=1.1.0&request=GetMap&layers=nurc%3AArc_Sample'
                             '&bbox=-180.0%2C-90.0%2C180.0%2C90.0&width=768&height=384&srs=EPSG%3A4326&styles='
                             '&format=application/openlayers',
             'request_type': 'GET',
             'user_agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0',
             'app_name': 'geoserver',
             'app_details': None,
             'response_time': 18,
             'response_size': None,
             'http_code': 200
        }
        self.assertEqual(data, expected_data)


    def test_read_logline_traefik_georhena_format(self):
        logformat = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms"
        logline = '5.172.196.188 - - [01/Jun/2023:00:00:11 +0000] ' \
                  '"GET /geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities HTTP/1.1" ' \
                  '200 19843 "-" "-" 1 "proxy@docker" "http://172.18.0.11:8080" 57ms'
        logentry = apachelogs.parse_lines(logformat, [logline])
        data = core.collect_common_data(next(logentry))
        expected_data = {
            'timestamptz': '2023-06-01T00:00:11+00:00',
             'username': None,
             'org': None,
             'roles': None,
             'request_path': '/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities',
             'request_type': 'GET',
             'user_agent': None,
             'app_name': 'geoserver',
             'app_details': None,
             'response_time': 57,
             'response_size': 19843,
             'http_code': 200
        }
        self.assertEqual(data, expected_data)


class TestProcess(unittest.TestCase):
    def test_read_logline(self):
        logformat = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" - \"%{app}n\" \"-\" %{ms}Tms"
        logline = '192.168.1.70 - testadmin|Project Steering Committee|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN,ROLE_USER,' \
                  'ROLE_ADMINISTRATOR,ROLE_GN_ADMIN,ROLE_EMAILPROXY [18/Oct/2023:17:36:06 +0000] ' \
                  '"GET /geoserver/nurc/wms?service=WMS&version=1.1.0&request=GetMap&layers=nurc%3AArc_Sample' \
                  '&bbox=-180.0%2C-90.0%2C180.0%2C90.0&width=768&height=384&srs=EPSG%3A4326&styles=' \
                  '&format=application/openlayers HTTP/1.1" 200 - "-" ' \
                  '"Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0" - "geoserver" "-" 18ms'
        logentry = apachelogs.parse_lines(logformat, [logline])
        data = core.process(next(logentry))
        expected_data = {
            'timestamptz': '2023-10-18T17:36:06+00:00',
             'username': 'testadmin',
             'org': 'Project Steering Committee',
             'roles': 'ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN,ROLE_USER,ROLE_ADMINISTRATOR,ROLE_GN_ADMIN,ROLE_EMAILPROXY',
             'request_path': '/geoserver/nurc/wms?service=WMS&version=1.1.0&request=GetMap&layers=nurc%3AArc_Sample'
                             '&bbox=-180.0%2C-90.0%2C180.0%2C90.0&width=768&height=384&srs=EPSG%3A4326&styles='
                             '&format=application/openlayers',
             'request_type': 'GET',
             'user_agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0',
             'app_name': 'geoserver',
             'app_details': {
                    "service": "wms",
                    "request": "getmap",
                    "format": "application/openlayers",
                    "workspace": "nurc",
                    "layers": "arc_sample",
                    "projection": "EPSG:4326",
                    "version": "1.1.0",
                    "size": "768x384",
                    # "tiled": "false",
                    "bbox": "-180.0,-90.0,180.0,90.0"
                },
             'response_time': 18,
             'response_size': None,
             'http_code': 200
        }
        self.assertEqual(data, expected_data)


    def test_read_logline_traefik_georhena_format(self):
        logformat = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms"
        logline = '5.172.196.188 - - [01/Jun/2023:00:00:11 +0000] ' \
                  '"GET /geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities HTTP/1.1" ' \
                  '200 19843 "-" "-" 1 "proxy@docker" "http://172.18.0.11:8080" 57ms'
        logentry = apachelogs.parse_lines(logformat, [logline])
        data = core.process(next(logentry))
        expected_data = {
            'timestamptz': '2023-06-01T00:00:11+00:00',
             'username': None,
             'org': None,
             'roles': None,
             'request_path': '/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities',
             'request_type': 'GET',
             'user_agent': None,
             'app_name': 'geoserver',
             'app_details': {
                    "service": "wms",
                    "request": "getcapabilities",
                    "version": "1.3.0",
                },
             'response_time': 57,
             'response_size': 19843,
             'http_code': 200
        }
        self.assertEqual(data, expected_data)


if __name__ == '__main__':
    unittest.main()
