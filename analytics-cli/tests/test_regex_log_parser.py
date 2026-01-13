import re
from datetime import datetime
import os
from dateutil import parser as dtparser
from dateutil.tz import tzutc
from georchestra_analytics_cli.access_logs.log_parsers.RegexLogParser import RegexLogParser
from georchestra_analytics_cli.config import load_config_from

config_file = os.path.join(os.path.dirname(__file__), "config_files/config.yaml")
config_file2 = os.path.join(os.path.dirname(__file__), "config_files/config_multiple_dn.yaml")


def test_create_parser():
    conf = load_config_from(config_file)
    log_parser = RegexLogParser(conf)
    assert log_parser is not None


def test_set_regex():
    conf = load_config_from(config_file)
    log_parser = RegexLogParser(conf)
    regex = r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (?P<span_id>\w+) (?P<trace_id>\w+) (?P<message>.*)"
    log_parser.set_regex(regex)
    assert log_parser.log_format_regex == re.compile(regex)


def test_set_extra_info():
    conf = load_config_from(config_file)
    log_parser = RegexLogParser(conf)
    extrainfo = {"server_address": "demo.georchestra.org", "app_path": "/"}
    log_parser.set_extra_info(extrainfo)
    assert log_parser.extra_info == extrainfo


def test_get_app_path():
    conf = load_config_from(config_file)
    log_parser = RegexLogParser(conf)
    assert log_parser.get_app_path({"app_path": "/geoserver/"}) == "/geoserver/"
    assert log_parser.get_app_path({}) is None


def test_get_user_info():
    conf = load_config_from(config_file)
    log_parser = RegexLogParser(conf)
    ui = "testadmin|PSC|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN"
    assert log_parser._get_user_info(ui) == {
        "name": "testadmin",
        "org": "PSC",
        "roles": ["ROLE_SUPERUSER", "ROLE_MAPSTORE_ADMIN"]}


def test_get_response_time():
    conf = load_config_from(config_file2)
    log_parser = RegexLogParser(conf)
    assert log_parser._get_response_time(1.32) == 1320


def test_parse_regex_lines():
    conf = load_config_from(config_file)
    log_parser = RegexLogParser(conf)
    record = '192.168.1.70 - testadmin|Project Steering Committee|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN,ROLE_USER,ROLE_ADMINISTRATOR,ROLE_GN_ADMIN,ROLE_EMAILPROXY [18/Oct/2023:17:36:10 +0000] "GET /geoserver/sf/wms?service=WMS&version=1.1.0&request=GetMap&layers=sf%3Aroads&bbox=589434.8564686741%2C4914006.337837095%2C609527.2102150217%2C4928063.398014731&width=768&height=537&srs=EPSG%3A26713&styles=&format=application/openlayers HTTP/1.1" 200 - "-" "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0" - "geoserver" "-" 18ms'
    expected_parsed_record = {
        'app_id': 'geoserver',
        'app_name': 'geoserver',
        'app_path': 'geoserver',
        'auth_method': None,
        'client_ip': '',
        'context_data': {'source_type': 'access_log_file'},
        'id': '06e35f9d47da',
        'message': '192.168.1.70 - testadmin|Project Steering '
                   'Committee|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN,ROLE_USER,ROLE_ADMINISTRATOR,ROLE_GN_ADMIN,ROLE_EMAILPROXY '
                   '[18/Oct/2023:17:36:10 +0000] "GET '
                   '/geoserver/sf/wms?service=WMS&version=1.1.0&request=GetMap&layers=sf%3Aroads&bbox=589434.8564686741%2C4914006.337837095%2C609527.2102150217%2C4928063.398014731&width=768&height=537&srs=EPSG%3A26713&styles=&format=application/openlayers '
                   'HTTP/1.1" 200 - "-" "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) '
                   'Gecko/20100101 Firefox/102.0" - "geoserver" "-" 18ms',
        'org_id': 'Project Steering Committee',
        'org_name': 'Project Steering Committee',
        'request_details': {
            'bbox': '589434.8564686741,4914006.337837095,609527.2102150217,4928063.398014731',
            'crs': 'EPSG:26713',
            'format': 'application/openlayers',
            'height': '537',
            'layers': 'roads',
            'os_family': 'Linux',
            'os_version': None,
            'request': 'getmap',
            'service': 'WMS',
            'size': '768x537',
            'user_agent_family': 'Firefox',
            'user_agent_string': 'Mozilla/5.0 (X11; Linux x86_64; '
                                 'rv:102.0) Gecko/20100101 '
                                 'Firefox/102.0',
            'user_agent_version': '102.0',
            'version': '1.1.0',
            'width': '768',
            'workspaces': 'sf',
            'tags': ['ogc']
        },
        'request_method': 'GET',
        'request_path': '/geoserver/sf/wms',
        'request_query_string': 'service=wms&version=1.1.0&request=getmap&layers=sf%3aroads&bbox=589434.8564686741%2c4914006.337837095%2c609527.2102150217%2c4928063.398014731&width=768&height=537&srs=epsg%3a26713&styles=&format=application/openlayers',
        'response_size': None,
        'response_time': 18000,
        'roles': [
            'ROLE_SUPERUSER',
            'ROLE_MAPSTORE_ADMIN',
            'ROLE_USER',
            'ROLE_ADMINISTRATOR',
            'ROLE_GN_ADMIN',
            'ROLE_EMAILPROXY'
        ],
        'server_address': '',
        'status_code': 200,
        'ts': '2023-10-18T17:36:10+00:00',
        'user_id': 'testadmin',
        'user_name': 'testadmin'
    }

    assert log_parser.parse(record) == expected_parsed_record


def test_parse_regex_multipledn():
    conf = load_config_from(config_file2)
    log_parser = RegexLogParser(conf)
    log_parser.set_extra_info({"server_address": "mapserv.georchestra.org", "app_path": "/"})
    record = '127.0.0.1 127.0.1.1 unix:/var/run/mapserv-1.sock - [10/Dec/2025:05:39:15 +0100] "GET /ortho?transparent=True&layers=ortho_2022&format=image%2Fpng&bbox=792478.4366714223,6543339.050380466,792585.9236505884,6543446.537359633&width=1300&height=1300&srs=EPSG%3A2154&request=GetMap&version=1.1.1&service=WMS&styles= HTTP/1.1" 200 2560412 "-" "MapProxy-1.15.1" 0.626'
    expected_parsed_record = {
        'ts': '2025-12-10T05:39:15+01:00',
        'id': 'd963d4e17b84',
        'message': '127.0.0.1 127.0.1.1 unix:/var/run/mapserv-1.sock - [10/Dec/2025:05:39:15 +0100] "GET /ortho?transparent=True&layers=ortho_2022&format=image%2Fpng&bbox=792478.4366714223,6543339.050380466,792585.9236505884,6543446.537359633&width=1300&height=1300&srs=EPSG%3A2154&request=GetMap&version=1.1.1&service=WMS&styles= HTTP/1.1" 200 2560412 "-" "MapProxy-1.15.1" 0.626',
        'app_id': 'mapserv.georchestra.org/',
        'app_path': '/',
        'app_name': 'mapserver',
        'user_id': None,
        'user_name': None,
        'org_id': None,
        'org_name': None,
        'roles': None,
        'auth_method': None,
        'request_method': 'GET',
        'request_path': '/ortho',
        'request_query_string': 'transparent=true&layers=ortho_2022&format=image%2fpng&bbox=792478.4366714223,6543339.050380466,792585.9236505884,6543446.537359633&width=1300&height=1300&srs=epsg%3a2154&request=getmap&version=1.1.1&service=wms&styles=',
        'request_details': {'bbox': '792478.4366714223,6543339.050380466,792585.9236505884,6543446.537359633',
                            'format': 'image/png', 'height': '1300', 'layers': 'ortho_2022', 'workspaces': '/ortho',
                            'request': 'getmap', 'service': 'WMS', 'crs': 'EPSG:2154', 'transparent': 'true',
                            'user_agent_string': 'MapProxy-1.15.1', 'version': '1.1.1', 'width': '1300',
                            'size': '1300x1300', 'tags': ['ogc']},
        'response_time': 626,
        'response_size': 2560412,
        'status_code': 200,
        'client_ip': '127.0.0.1',
        'server_address': 'mapserv.georchestra.org',
        'context_data': {'source_type': 'access_log_file'},

    }

    assert log_parser.parse(record) == expected_parsed_record
