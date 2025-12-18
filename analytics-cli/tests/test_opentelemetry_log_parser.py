from datetime import datetime
import os
from dateutil import parser as dtparser
from dateutil.tz import tzutc
from georchestra_analytics_cli.access_logs.log_parsers.OpentelemetryLogParser import OpentelemetryLogParser
from georchestra_analytics_cli.common.models import OpentelemetryAccessLogRecord
from georchestra_analytics_cli.config import load_config_from
from data.otel_records import otel_record1

config_file = os.path.join(os.path.dirname(__file__), "config_files/config.yaml")



def test_create_parser():
    conf = load_config_from(config_file)
    log_parser = OpentelemetryLogParser(conf)
    assert log_parser is not None

def test_get_app_path():
    conf = load_config_from(config_file)
    log_parser = OpentelemetryLogParser(conf)
    assert log_parser.get_app_path("/geoserver/myws/wms") == "/geoserver/"

def test_read_otel_generics():
    conf = load_config_from(config_file)
    log_parser = OpentelemetryLogParser(conf)
    otel_record = OpentelemetryAccessLogRecord(
        dtparser.parse(otel_record1.get('timestamp')),
        otel_record1.get('span_id'),
        otel_record1.get('trace_id'),
        otel_record1.get('message'),
        otel_record1.get('attributes'),
        otel_record1.get('resources'),
        otel_record1.get('scope'),
        otel_record1.get('source_type'),
        otel_record1.get('severity_text'),
        otel_record1.get('severity_number'),
        otel_record1.get('observed_timestamp'),
        otel_record1.get('flags'),
        otel_record1.get('dropped_attributes_count'),
    )
    expected_otel_generics = {
            "ts": datetime(2025, 12, 17, 13, 19, 38, 491768, tzinfo=tzutc()),
            "id": otel_record1.get('span_id'),
            "message": otel_record1.get('message'),
            "context_data": {
                "source_type": otel_record1.get('source_type'),
                "span_id": otel_record1.get('span_id'),
                "trace_id": otel_record1.get('trace_id'),
                "logger": otel_record1["scope"].get("name", "")
            }
    }

    assert log_parser.read_otel_generics(otel_record) == expected_otel_generics


def test_read_otel_mdc():
    conf = load_config_from(config_file)
    log_parser = OpentelemetryLogParser(conf)
    otel_record = OpentelemetryAccessLogRecord(
        dtparser.parse(otel_record1.get('timestamp')),
        otel_record1.get('span_id'),
        otel_record1.get('trace_id'),
        otel_record1.get('message'),
        otel_record1.get('attributes'),
        otel_record1.get('resources'),
        otel_record1.get('scope'),
        otel_record1.get('source_type'),
        otel_record1.get('severity_text'),
        otel_record1.get('severity_number'),
        otel_record1.get('observed_timestamp'),
        otel_record1.get('flags'),
        otel_record1.get('dropped_attributes_count'),
    )
    expected_otel_mdc = {
        "app_id": "/geoserver/",
        "app_path": "/geoserver/",
        "app_name": "geoserver",
        "user_id": "0c6bb556-4ee8-46f2-892d-6116e262b489",
        "user_name": "testadmin",
        "org_id": "bddf474d-125d-4b18-92bd-bd8ebb6699a9",
        "org_name": "PSC",
        "roles": ["ROLE_SUPERUSER", "ROLE_MAPSTORE_ADMIN", "ROLE_USER", "ROLE_ADMINISTRATOR", "ROLE_SUPERSET_ADMIN", "ROLE_GN_ADMIN", "ROLE_EMAILPROXY", "ROLE_IMPORT"],
        "auth_method": "GeorchestraUserNamePasswordAuthenticationToken",
        "request_method": "GET",
        "request_path": "/geoserver/psc/wms",
        "request_query_string": "service=wms&version=1.1.1&request=getmap&format=image%2fpng&transparent=true&styles&layers=psc%3acours_eau&exceptions=application%2fvnd.ogc.se_inimage&srs=epsg%3a2154&width=769&height=537&bbox=532322.3855297221%2c6226308.935051317%2c766874.0734739716%2c6390006.467262409",
        "request_details": {
            'bbox': '532322.3855297221,6226308.935051317,766874.0734739716,6390006.467262409',
            'exceptions': 'application/vnd.ogc.se_inimage',
            'format': 'image/png',
            'height': '537',
            'layers': 'psc:cours_eau',
            'request': 'GetMap',
            'service': 'WMS',
            'srs': 'EPSG:2154',
            'styles': 'null',
            'transparent': 'true',
            'version': '1.1.1',
            'width': '769',
            'os_family': 'Linux',
            'os_version': None,
            'user_agent_family': 'Firefox',
            'user_agent_string': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 '
            'Firefox/140.0',
            'user_agent_version': '140.0',
        },
        "response_time": None,
        "response_size": None,
        "status_code": 200,
        "client_ip": "",
        "server_address": "georchestra-127-0-0-1.nip.io",
    }

    assert log_parser.read_otel_mdc(otel_record) == expected_otel_mdc
