import logging
from typing import Any
from ua_parser import parse

from georchestra_analytics_cli.access_logs.log_parsers.BaseLogParser import BaseLogParser
from georchestra_analytics_cli.access_logs.log_parsers.RegexLogParser import RegexLogParser
from georchestra_analytics_cli.common.models import OpentelemetryAccessLogRecord
from georchestra_analytics_cli.config import Config
from georchestra_analytics_cli.utils import int_or_none, dict_recursive_update, split_url, split_query_string

logger = logging.getLogger(__name__)


class OpentelemetryLogParser(BaseLogParser):
    """
    Parse log messages as they come from OpenTelemetry standard. It is expected to collect the interesting data as
    MDC attributes. Eventually it can complement the information by parsing the log textual message. Since this implies
    additional processing, it is not done by default, it has to be configured in the config file.
    When parsing textual log message, it relies on the RegexLogParser class and the pattern of the log message can
    be adapted through a regular expression provided in config.
    """
    config: Config = None
    regex_log_parser: RegexLogParser = None

    def __init__(self, config: Config):
        self.config = config
        otel_config = self.config.get_parser_config_opentelemetry()
        if otel_config["text_message_parser"]["enable"]:
            self.regex_log_parser = RegexLogParser(config)
            if otel_config["text_message_parser"].has_key("regex"):
                self.regex_log_parser.set_regex(otel_config["text_message_parser"]["regex"])

        super().__init__(config)

    def parse(self, otel_record: OpentelemetryAccessLogRecord) -> dict[str, Any]:
        """
        Parses an access log message provided in the format managed by the implementation class and returns a dictionary with
        the parsed values, matching the common.models.AccessLogRecord schema.
        """
        log_dict = self.read_otel_generics(otel_record)
        if self.regex_log_parser is not None:
            dict_recursive_update(log_dict, self.regex_log_parser.parse(otel_record.message))

        dict_recursive_update(log_dict, self.read_otel_mdc(otel_record))
        # And then add app-specific logic
        if log_dict.get("app_path", None) and log_dict.get("app_name", None):
            lp = self._get_app_processor(log_dict["app_name"], log_dict["app_path"])
            if not (lp and lp.is_relevant(log_dict["request_path"], log_dict.get("request_query_string", ""))):
                logging.debug(f"drop    {log_dict.get('message')}")
                return None
            logging.debug(f"pass    {log_dict.get('message')}")
            app_data = lp.collect_information(log_dict.get("request_path", ""), log_dict.get("request_details", {}))
            if app_data is not None:
                # We replace the request_details dict, instead of simply updating it. It allows to drop some values deemed uninteresting/redundant
                # dict_recursive_update(log_dict["request_details"], app_data)
                log_dict["request_details"] = app_data
        return log_dict

    def read_otel_generics(self, otel_record: OpentelemetryAccessLogRecord) -> dict[str, Any]:
        """
        Get the information that we can expect to always be there and might be useful
        """
        log_dict = {
            # "oid": None,
            "ts": otel_record.timestamp,
            "id": otel_record.span_id,
            "message": otel_record.message,
            "context_data": {
                "source_type": otel_record.source_type,
                "span_id": otel_record.span_id,
                "trace_id": otel_record.trace_id,
                "logger": otel_record.scope.get("name", "")
            }
        }
        return log_dict

    def read_otel_mdc(self, otel_record: OpentelemetryAccessLogRecord) -> dict[str, Any]:
        """
        Retrieve data from the MDC data (stored by Otel in "attributes")
        """
        attributes = otel_record.attributes or dict()
        u_path, u_request_qs, u_fragments = split_url(attributes.get("http.request.url", "").lower())
        request_path = attributes.get("http.request.path", "").lower() or u_path
        app_path = self.get_app_path(request_path)
        log_dict = {
            "app_path": app_path,
            "app_name": self.config.what_app_is_it(app_path),
            "user_id": attributes.get("enduser.uuid", ""),
            "user_name": attributes.get("enduser.id", ""),
            "org_id": attributes.get("enduser.org.uuid", ""),
            "org_name": attributes.get("enduser.org.id", ""),
            "roles": attributes.get("enduser.roles", "").split(","),
            "auth_method": attributes.get("enduser.auth-method", ""),
            "request_method": attributes.get("http.request.method", "").upper(),
            "request_path": request_path,
            "request_query_string": attributes.get("http.request.query-string", "").lower() or u_request_qs,
            "request_details": {k.split(".")[-1].lower(): v for k, v in attributes.items() if
                                k.startswith("http.request.parameter.")},
            "response_time": int_or_none(attributes.get("http.response.duration_ms", "")),
            "response_size": int_or_none(attributes.get("http.response.body.size_bytes", "")),
            "status_code": int_or_none(attributes.get("http.status_code", "")),
        }
        # If request params are absent, we'll get them from the URL
        if not log_dict["request_details"] and u_request_qs:
            log_dict["request_details"] = split_query_string(u_request_qs)

        # Append user-agent header information
        # TODO: above, match request_details extraction with a regex rather, it would allow to add this one on-the-go
        user_agent = attributes.get("http.request.header.User-Agent", "")
        if user_agent:
            ua_dict = self.parse_user_agent(user_agent)
            log_dict["request_details"].update(ua_dict)
        return log_dict

    def get_app_path(self, request_path: str) -> str:
        """
        Extract app path from the request string (e.g. /app_path/1/2/3)
        """
        try:
            app_path = request_path.split("/")[1]
        except IndexError as e:
            # TODO: maybe raise LogParseError
            return None
        return app_path.lower()

    @staticmethod
    def parse_user_agent(user_agent):
        """
        Parse the User-Agent string. Tries to extract important information while keeping an reasonably low cardinality
        (the more diversity we get in the results, the harder it will be to aggregate the values in the exploitation
        views)
        """
        ua = parse(user_agent)
        # Keep only the best bits
        ua_dict_info = {
            "user_agent_string": user_agent
        }
        if ua.user_agent:
            ua_dict_info["user_agent_family"] = ua.user_agent.family
            ua_dict_info["user_agent_version"] = f"{ua.user_agent.major}.{ua.user_agent.minor}"
        # Information about the OS used
        if ua.os:
            ua_dict_info["os_family"] = ua.os.family
            ua_dict_info["os_version"] = ua.os.major
        # Information about the device (should allow to deduce if mobile phone or computer
        if ua.device:
            ua_dict_info["device_family"] = ua.device.family
            ua_dict_info["device_brand"] = ua.device.brand
            ua_dict_info["device_model"] = ua.device.model
        return ua_dict_info
