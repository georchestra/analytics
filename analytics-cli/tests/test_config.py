import os

from georchestra_analytics_cli.config import Config, get_config, load_config_from

config_file = os.path.join(os.path.dirname(__file__), "config_files/config.yaml")
config_multiple_dn = os.path.join(os.path.dirname(__file__), "config_files/config_multiple_dn.yaml")


def test_config_default():
    conf = get_config()
    assert isinstance(conf, Config)
    assert 'app_processors' in conf.config
    assert 'apps_mapping' in conf.config
    assert 'database' in conf.config
    assert 'logging' in conf.config
    assert 'parsers' in conf.config
    assert 'performance' in conf.config
    assert conf.get_batch_size() == 10000

def test_config_load_from_file():
    conf = load_config_from(config_file)
    assert conf.is_metrics_enabled() == True
    assert conf.get_batch_size() == 100

def test_config_db():
    conf = load_config_from(config_file)
    assert conf.get_db_connection_string().render_as_string(True) == "postgresql://tsdb:***@localhost:5433/analytics"
    assert conf.get_db_connection_string().render_as_string(
        False) == "postgresql://tsdb:secret@localhost:5433/analytics"


def test_config_db_env():
    os.environ["DB_SECRET"] = "secretpassword"
    conf = load_config_from(config_file)
    assert conf.get_db_connection_string().render_as_string(
        False) == "postgresql://tsdb:secretpassword@localhost:5433/analytics"
    os.environ.pop("DB_SECRET")

def test_config_app_mapping_basic():
    conf = load_config_from(config_file)
    assert conf.what_app_is_it("/geoserver/") == "geoserver"
    assert conf.what_app_is_it("/data/") == "dataapi"

def test_config_app_mapping_multiple_dn():
    conf = load_config_from(config_multiple_dn)
    assert conf.what_app_is_it("demo.georchestra.org/catalog/") == "geonetwork"
    assert conf.what_app_is_it("mapserv.georchestra.org/") == "mapserver"
    # This one covers a non-delcared mapping
    assert conf.what_app_is_it("mapproxy.georchestra.org/") == "mapproxy.georchestra.org"

def test_config_keys_blacklist():
    conf = load_config_from(config_file)
    assert conf.get_keys_blacklist() == ["user_id", "user_name", "roles"]

def test_config_keys_blacklist_empty():
    conf = load_config_from(config_multiple_dn)
    assert conf.get_keys_blacklist() == []