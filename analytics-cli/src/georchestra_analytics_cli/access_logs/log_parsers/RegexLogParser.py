import logging
import re
from urllib.parse import parse_qs, urlparse

from dateutil import parser as dateutil_parser
from typing import Any, Tuple
import hashlib

from georchestra_analytics_cli.access_logs.log_parsers.BaseLogParser import BaseLogParser
from georchestra_analytics_cli.utils import int_or_none, split_url, split_query_string, dict_recursive_update
from georchestra_analytics_cli.config import Config

logger = logging.getLogger(__name__)


class RegexLogParser(BaseLogParser):
    """
    Parser class for textual access log messages based on regular expressions.
    Access log messages are expected to follow reasonably standardized formats like CLF
    (https://en.wikipedia.org/wiki/Common_Log_Format) which in theory makes them quite easy to parse
    using regular expressions.
    """
    # Regex for CLF access logs
    default_log_format_regex_str = r"^(?P<ip>[0-9a-fA-F:\.]+) (?P<user_identifier>[-_\w]+) (?P<user>[-_\|, \w]+) \[(?P<timestamp>.*)\] \"(?P<method>GET|POST|HEAD|OPTION|PUT|PATCH|DELETE|TRACE|CONNECT) (https?:\/\/[_:a-zA-Z0-9\.-]+)?(?P<path>\/(?P<app>[_a-zA-Z0-9-]+)(\/.*)) HTTP\/[\.0-9]{3}\" (?P<status_code>[0-9]{3}) (?P<response_size>[-0-9]*)"

    log_format_regex = None
    config: Config = None
    hashl = None

    def __init__(self, config: config):
        self.config = config
        log_format_regex_str = config.get_parser_config_textmsg().get("regex", self.default_log_format_regex_str)
        self.log_format_regex = re.compile(log_format_regex_str)
        # hashlib is used to generate a hashed key identifying the log message so that we can handle duplicates
        self.hashl = hashlib.md5()
        super().__init__(config)

    def set_regex(self, regex_str):
        """
        Allows to change the regex used for the parsing
        """
        self.log_format_regex = re.compile(regex_str)

    def parse(self, msg: str) -> dict[str, Any]:
        """
        Uses the regular expression to parse a log message and return a dictionary with the parsed values.
        """
        m = re.match(self.log_format_regex, msg)
        if not m:
            return None
        m_dict = m.groupdict()

        # Clean non defined values
        for k, v in m_dict.items():
            if v == "-":
                m_dict[k] = None

        ts = dateutil_parser.parse(m_dict["timestamp"].replace(":", " ", 1))
        app_path =self.get_app_path(m_dict)
        if app_path is None:
            # If no app path is extracted, we consider the log record invalid
            return None
        path, qs, fragment = split_url(m_dict.get("path", ""))
        log_dict = {
            "ts": ts.isoformat(),
            "id": self.generate_req_id(msg),
            "message": msg,
            "app_path": app_path,
            "app_name": self.config.what_app_is_it(app_path),
            "user_id": self._get_user_info(m_dict.get("user", "")).get("name"),
            "user_name": self._get_user_info(m_dict.get("user", "")).get("name"),
            "org_id": self._get_user_info(m_dict.get("user", "")).get("org"),
            "org_name": self._get_user_info(m_dict.get("user", "")).get("org"),
            "roles": self._get_user_info(m_dict.get("user", "")).get("roles"),
            "auth_method": None,
            "request_method": m_dict.get("method", ""),
            "request_path": path,
            "request_query_string": qs,
            # "user_agent": m_dict.get("user_agent", ""),
            "request_details": split_query_string(qs),
            "response_time": int_or_none(m_dict.get("response_time")),
            "response_size": int_or_none(m_dict.get("response_size")),
            "status_code": int_or_none(m_dict.get("status_code", "")),
            "context_data": {
                "source_type": "access_log_file",
            }
        }

        # And then add app-specific logic
        app_data = self.parse_with_app_processor(log_dict)
        if app_data is not None:
            # We replace the request_details dict, instead of simply updating it. It allows to drop some values deemed uninteresting/redundant
            # dict_recursive_update(log_dict["request_details"], app_data)
            log_dict["request_details"] = app_data
        return log_dict

    def get_app_path(self, m_dict: dict[str, Any]) -> str:
        app_path = m_dict.get("app", "").lower()
        if not app_path:
            # TODO: maybe raise LogParseError
            return None
        return app_path

    @staticmethod
    def _get_user_info(user_string: str) -> dict:
        """
        The user information can be provided in a single |-separated string. Extract this info
        and store it in a structured way
        :param user_string: expecting something like testadmin|Project Steering Committee|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN
        :return: dict {"name": thename, "org": theorg, "roles": [the roles]}
        """
        if not user_string:
            return dict()
        user_categories = ["name", "org", "roles"]
        user_values = [None, None, None]
        if user_string:
            user_values = user_string.split("|")
        user_info = {
            "name": user_values[0],
            "org": user_values[1],
            "roles": user_values[2].split(",")
        }
        # user_info = dict(zip(user_categories, user_values))
        # # Make roles a list
        # user_info["roles"] = user_info["roles"].split(",")
        return user_info

    def generate_req_id(self, msg):
        """
        Generate an ID for this log line. Will serve to avoid inserting duplicates. Replaces the span_id that we get
        with OpenTelemetry
        """
        self.hashl.update(msg.encode('utf-8'))
        return self.hashl.hexdigest()[0:12]

