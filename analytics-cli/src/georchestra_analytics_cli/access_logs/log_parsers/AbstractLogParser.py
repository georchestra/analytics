"""
Abstract log parser. Defines an interface to be followed when implementing log parser classes.
A log parser reads access logs from a data source, extracts the information in a format suitable
for analytics works and returns it in a dict structure compatible with common.models.AccessLogRecord
"""

from abc import ABC, abstractmethod
from typing import Tuple, Any

from georchestra_analytics_cli.common.models import AccessLogRecord


class AbstractLogParser(ABC):
    config = None

    @abstractmethod
    def __init__(self, config):
        """
        Initialize with a parser dict issued from georchestra_analytics_cli.config.Config.
        """
        pass

    @abstractmethod
    def parse(self, log_record: Any) -> dict[str, Any]:
        """
        Parses an access log message in the format managed by the implementation class and returns a dictionary with
        the parsed values, matching the common.models.AccessLogRecord schema.
        """
        pass