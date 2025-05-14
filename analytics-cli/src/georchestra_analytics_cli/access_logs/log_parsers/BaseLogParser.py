import importlib
import logging
from typing import Any

from georchestra_analytics_cli.access_logs.log_parsers.AbstractLogParser import AbstractLogParser
from georchestra_analytics_cli.config import Config

logger = logging.getLogger(__name__)


class BaseLogParser(AbstractLogParser):
    """
    Base for implementing log Parsers. Not intended to be used directly.
    """
    config: Config = None
    app_processors_config: dict[str, Any] = None
    app_processors: dict[str, Any] = {}

    def __init__(self, config: Config):
        self.config = config
        self.app_processors_config = config.get_app_processors_config()

    def parse(self, log_record: Any) -> dict[str, Any]:
        """
        not implemented
        """
        return None

    def _get_app_processor(self, app_name, app_path):
        """
        Lazy-load the log processors for each app we might encounter.
        """
        if app_path in self.app_processors.keys():
            return self.app_processors[app_path]

        # else:
        try:
            app_module = importlib.import_module(
                f"georchestra_analytics_cli.access_logs.app_processors.{app_name.lower()}"
            )
            app_processor_class_ = getattr(app_module, f"{app_name.capitalize()}LogProcessor")
            cfg = self.app_processors_config.get(app_name.lower(), {})
            self.app_processors[app_name] = app_processor_class_(app_path=app_path, config=cfg)
        except ModuleNotFoundError as e:
            if self.app_processors_config.get("fallback_on_generic", False) is True:
                logging.debug(
                    f"Log processor for app {app_name} not found. Falling back with generic log processor"
                )
                self.app_processors[app_path] = importlib.import_module(
                    f"georchestra_analytics_cli.access_logs.app_processors.generic"
                ).GenericLogProcessor()
            else:
                logging.debug(f"Log processor for app {app_path} not found. Dropping this line")
                return None
        return self.app_processors[app_path]
