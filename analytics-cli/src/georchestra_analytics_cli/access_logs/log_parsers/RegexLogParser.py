import hashlib
import logging
import re
from typing import Any, Tuple
from urllib.parse import parse_qs, urlparse

from dateutil import parser as dateutil_parser

from georchestra_analytics_cli.access_logs.log_parsers.BaseLogParser import (
    BaseLogParser,
)
from georchestra_analytics_cli.config import Config
from georchestra_analytics_cli.utils import (
    dict_recursive_update,
    float_or_none,
    generate_app_id,
    int_or_none,
    split_query_string,
    split_url,
)

logger = logging.getLogger(__name__)


class RegexLogParser(BaseLogParser):
    """
    Parser class for textual access log messages based on regular expressions.
    Access log messages are expected to follow reasonably standardized formats like CLF
    (https://en.wikipedia.org/wiki/Common_Log_Format) which in theory makes them quite easy to parse
    using regular expressions.
    """

    # Regex for CLF access logs
    default_log_format_regex_str = r"^(?P<ip>[0-9a-fA-F:\.]+) (?P<user_identifier>[-_\w]+) (?P<user>[-_\|, \w]+) \[(?P<timestamp>.*)\] \"(?P<method>GET|POST|HEAD|OPTION|PUT|PATCH|DELETE|TRACE|CONNECT) (https?:\/\/[_:a-zA-Z0-9\.-]+)?(?P<path>(?P<app_path>\/[_a-zA-Z0-9-]+\/)(.*)) HTTP\/[\.0-9]{3}\" (?P<status_code>[0-9]{3}) (?P<response_size>[-0-9]*)"

    log_format_regex = None
    config: Config
    hashl = None
    # Can contain some values that can't be parsed from the log lines, but we want to add to all parsed records
    extra_info: dict[str, Any] = {}

    def __init__(self, config: Config):
        self.config = config
        log_format_regex_str = config.get_parser_config_textmsg().get(
            "regex", self.default_log_format_regex_str
        )
        self.log_format_regex = re.compile(log_format_regex_str)
        # hashlib is used to generate a hashed key identifying the log message so that we can handle duplicates
        self.hashl = hashlib.md5()
        super().__init__(config)

    def set_regex(self, regex_str):
        """
        Allows to change the regex used for the parsing
        """
        self.log_format_regex = re.compile(regex_str)

    def set_extra_info(self, extras: dict[str, Any]):
        """
        There are some information that might not be contained in the log lines, but that we want to include at a
        global level (all lines). For instance the host address. Or the app_id
        """
        self.extra_info = extras

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
        # Add extra attributes passed by commandline options
        m_dict.update(self.extra_info)

        ts = dateutil_parser.parse(m_dict["timestamp"].replace(":", " ", 1))

        # Determine app_path and app_id
        app_path = self.get_app_path(m_dict)
        app_id = m_dict.get("app_id")
        if not app_id:
            if self.config.is_supporting_multiple_dn():
                if m_dict.get("server_address") and app_path:
                    app_id_components = [m_dict.get("server_address"), app_path]
                    app_id = generate_app_id(app_id_components)
                else:
                    logger.error(
                        f"Missing elements to generate the app_id. Maybe you need to provide server_address and "
                        f"app_path through the CLI --extra_info arguments"
                    )
                    # TODO: maybe raise error and stop the run
            else:
                app_id = generate_app_id([app_path])

        if app_path is None and app_id is None:
            # If no app path is extracted and no app_id was provided, we consider the log record invalid
            return None
        hostname, path, qs, fragment = split_url(m_dict.get("path", ""))
        log_dict = {
            "ts": ts.isoformat(),
            "id": self.generate_req_id(msg),
            "message": msg,
            "app_id": app_id,
            "app_path": app_path,
            "app_name": self.config.what_app_is_it(app_id),
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
            "response_time": self._get_response_time(m_dict.get("response_time")),
            "response_size": int_or_none(m_dict.get("response_size")),
            "status_code": int_or_none(m_dict.get("status_code", "")),
            "client_ip": m_dict.get("client_ip", ""),
            "server_address": m_dict.get("server_address", ""),
            "context_data": {
                "source_type": "access_log_file",
            },
        }

        # Append user-agent header information
        user_agent = m_dict.get("user_agent", "")
        if user_agent:
            ua_dict = self.parse_user_agent(user_agent)
            log_dict["request_details"].update(ua_dict)

        # And then add app-specific logic
        app_data = self.parse_with_app_processor(log_dict)
        if app_data is not None:
            # We replace the request_details dict, instead of simply updating it. It allows to drop some values deemed uninteresting/redundant
            # dict_recursive_update(log_dict["request_details"], app_data)
            log_dict["request_details"] = app_data
        return log_dict

    def get_app_path(self, m_dict: dict[str, Any]) -> str:
        app_path = m_dict.get("app_path", "").lower()
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
            "roles": user_values[2].split(","),
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
        self.hashl.update(msg.encode("utf-8"))
        return self.hashl.hexdigest()[0:12]

    def _get_response_time(self, rt):
        """
        Response time can be  provided in seconds or ms. We harmonize it to ms
        """
        resp_time = float_or_none(rt)
        if not resp_time:
            return None

        if self.config.get_parser_config_textmsg().get("response_time_unit") == "s":
            resp_time = resp_time * 1000
        return int(resp_time)
