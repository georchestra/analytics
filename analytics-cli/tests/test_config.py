import os

from georchestra_analytics_cli.config import Config, get_config, load_config_from

config_file = os.path.join(os.path.dirname(__file__), "config_files/test_config.yaml")
config_db_file = os.path.join(os.path.dirname(__file__), "config_files/test_config_db.yaml")
config_db_file2 = os.path.join(os.path.dirname(__file__), "config_files/test_config_db2.yaml")
config_strategy2 = os.path.join(os.path.dirname(__file__), "config_files/wrong_strategy.yaml")


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
