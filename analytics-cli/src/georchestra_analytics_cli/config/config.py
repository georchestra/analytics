# Parse config file
import logging
from importlib import resources as impresources
from typing import Any

from pyaml_env import parse_config
from sqlalchemy.engine.url import URL as sqlalchemy_URL

from georchestra_analytics_cli.utils import dict_recursive_update

logger = logging.getLogger(__name__)

config: dict[str, Any] = None


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, config_path: str | None = None) -> None:
        self.config: dict[str, Any] = {}
        # Load default config
        with impresources.path(__package__, "analytics_cli.yaml") as fspath:
            result = fspath.stat()
            # Parse default config file
            self.config = parse_config(fspath)

        # Override with custom config passed on config_path file
        if config_path:
            try:
                # Recursively update the dict (dict.update doesn't do recursive)
                dict_recursive_update(self.config, parse_config(config_path))
            except IOError as err:
                logger.error(f"Failed to load config from file {config_path}: {err}")

    def get_db_connection_string(self) -> str:
        """
        Builds the connection string for the database connection,
        combining the different ways you can configure it
        (providing a dsn connection string, or a list of parameters, or a bit of both).
        To provide the password as an environment variable, look at an example in analytics_cli.yaml
        default config file.
        """
        db_config = self.config.get("database")
        # Get only relevant values
        conn_conf_dict = {
            key: db_config.get(key)
            for key in {
                "drivername",
                "host",
                "port",
                "database",
                "username",
                "password",
            }
        }
        connection_url = sqlalchemy_URL.create(**conn_conf_dict)
        logger.debug(f"db_conn_string='{connection_url}'")
        return connection_url

    def is_metrics_enabled(self) -> bool:
        return self.config["metrics"]["enabled"]

    def get_logging_config_as_dict(self) -> dict[str, Any]:
        return self.config["logging"]

    def get_apps_mapping(self) -> dict[str, str]:
        """
        apps_mapping is a dict of app_path:app_name, used to determine which *software* is running for a given path.
        Apps which path match the app name don't have to be listed.
        App names have to match the name used in this project's app_processors subpackage.

        e.g. let's suppose that we have a geonetwork instance running on /catalog. It can't be automatically inferred
        that this is a geonetwork instance. We'll have an apps_mapping entry like this:
            apps_mapping:
                catalog: geonetwork
        But we're not declaring the geoserver path, because it already corresponds to the geoserver app name.
        """
        return self.config.get("apps_mapping", {})

    def what_app_is_it(self, app_id: str):
        """
        If a mapping matches (taken from config) return the mapped app name.
        Else, the path is considered as the app name (less the trailing slashes)
        """
        app_mappings = self.config.get("apps_mapping", {})
        return app_mappings.get(app_id, app_id.strip("/"))

    def get_parser_config_opentelemetry(self) -> dict[str, Any]:
        return self.config["parsers"].get("opentelemetry", {})

    def get_parser_config_textmsg(self) -> dict[str, Any]:
        return self.config["parsers"].get("text_message", {})

    def get_batch_size(self) -> int:
        return self.config["performance"].get("batch_size", 1000)

    def get_keys_blacklist(self) -> list[str]:
        return self.config["data_privacy"].get("keys_blacklist", [])

    def get_app_processors_config(self) -> dict[str, Any]:
        return self.config.get("app_processors", {})

    def get_metrics_pushgateway_url(self) -> str:
        return self.config["metrics"].get("pushgateway_url")

    def get_metrics_metrics_file_path(self) -> str:
        return self.config["metrics"].get("metrics_file_path")

    def is_supporting_multiple_dn(self) -> bool:
        return self.config.get("support_multiple_dn", False)

    def get_timezone(self) -> str:
        return self.config.get("timezone", "UTC")


def get_config(config_path: str | None = None) -> Config:
    global config
    if config is None:
        config = Config(config_path)
    return config


def load_config_from(config_path: str | None = None) -> Config:
    global config
    config = Config(config_path)
    return config
