"""
Core log processing functions
- handle apache CLF logs files, extract common information
- call application-logic modules to extract information that is specific to each app
"""
import csv
import importlib
import json
import logging
import re
from dateutil import parser as dateutil_parser
import logging
from uuid import uuid4

# Default log format string, you can provide a custom one with the option logformat
common_log_format   = r'^(?P<ip>[0-9a-fA-F:\.]+) (?P<user_identifier>[-_\w]+) (?P<user>[-_\|, \w]+) \[(?P<timestamp>.*)\] \"(?P<method>GET|POST|HEAD|OPTION|PUT|PATCH|DELETE|TRACE|CONNECT) (https?:\/\/[_:a-zA-Z0-9\.-]+)?(?P<path>\/(?P<app>[_a-zA-Z0-9-]+)(\/.*)) HTTP\/[\.0-9]{3}\" (?P<status_code>[0-9]{3}) (?P<response_size>[-0-9]*)'
combined_log_format = r'^(?P<ip>[0-9a-fA-F:\.]+) (?P<user_identifier>[-_\w]+) (?P<user>[-_\|, \w]+) \[(?P<timestamp>.*)\] \"(?P<method>GET|POST|HEAD|OPTION|PUT|PATCH|DELETE|TRACE|CONNECT) (https?:\/\/[_:a-zA-Z0-9\.-]+)?(?P<path>\/(?P<app>[_a-zA-Z0-9-]+)(\/.*)) HTTP\/[\.0-9]{3}\" (?P<status_code>[0-9]{3}) (?P<response_size>[-0-9]*) "-" "(?P<user_agent>[-0-9a-zA-Z\/\.: ();_]*)" (?P<misc>.*) (?P<response_time>[0-9]+)ms$'
common_log_format_re = re.compile(common_log_format)
combined_log_format_re = re.compile(combined_log_format)


def process_log_file(log_file_path: str,
                     log_format: str = combined_log_format,
                     use_generic: bool = False) -> tuple[int, str]:
    """
    Take a log file, parse it using the defined parser format (default it combined_log_format above)
    Filter and process the log lines
    Output the result into a CSV file
    :param log_file_path:
    :param log_format: defines the parsing logic. Uses regular expressions https://docs.python.org/3/library/re.html
    :param use_generic: if True, use generic log processor for unsupported apps. If False, drop them
    :return: tuple (nb lines kept, csv file name)
    """
    try:
        log_format_re = re.compile(log_format)
    except:
        logging.error("Could not compile regular expression. Exit")
        return

    with open(log_file_path, 'r') as logs_data:
        processed_log_entries = []
        while True:
            line =  logs_data.readline()

            # if line is empty
            # end of file is reached
            if not line:
                break

            processed_log = process(line, log_format_re, use_generic)
            if (processed_log):
                # serialize the app_details dict
                processed_log["app_details"] = json.dumps(processed_log["app_details"])
                processed_log_entries.append(processed_log)
        csv_filename = _to_csv(processed_log_entries)
        return len(processed_log_entries), csv_filename
        # TODO Paginated publication


def process(line: str,
            log_format_regex: re.Pattern = combined_log_format_re,
            use_generic: bool = False) -> dict:
    """
    Process a single log line:
    - determines which log processor class to use for filtering and extracting app-specific data
    - collect common data
    - merge it all
    :param line: line of log
    :param log_format_regex: regular expression pattern to use
    :param use_generic: if True, use generic log processor for unsupported apps. If False, drop them
    :return: a dict containing all the gathered information. Or None if the line is filtered-out
    """

    # Extract common data from log line using regexp
    data = collect_common_data(line, log_format_regex)
    if not data:
        return None
    app = data["app_name"]
    path = data["request_path"]

    # logging.debug(f"processing log record for app {app}")

    log_processor = None
    # Next lines of code try to get the log processor class, implementation of AbstractLogProcessor, expected to be
    # provided by the package of the same name as the app (e.g. geoserver, geonetwork, mapstore etc)
    # If it doesn't find such a log processor class, it will fallback on a generic one.
    # Please do try to provide an app-specific one, since for now at least, the generic log processor does not filter any
    # line which might result in huge overhead for the storage database
    try:
        app_module = importlib.import_module(f"georchestra_access_logs_ingester.log_processors.{app.lower()}")
        log_processor_class_ = getattr(app_module, f"{app.capitalize()}LogProcessor")
        log_processor = log_processor_class_()
    except ModuleNotFoundError as e:
        if use_generic:
            logging.warning(f"Log processor for app {app} not found. Falling back with generic log processor")
            log_processor = importlib.import_module(f"georchestra_analytics.log_processors.generic").GenericLogProcessor()
        else:
            logging.warning(f"Log processor for app {app} not found. Drop line")
            return None

    # Filter out uninteresting lines (in regard to analytics needs)
    if not log_processor.is_relevant(path):
        logging.debug(f"dropped {path}")
        return None
    logging.debug(f"keep    {path}")
    custom_info = log_processor.collect_information(path)
    data["app_details"] = custom_info
    return data


def collect_common_data(line: str, log_format_regex: re.Pattern = combined_log_format_re) -> dict:
    """
    For a single parsed log line, collect all the information that will be common to all kind of apps
    (mostly, collects the chunks in the log line but does not process the URL structure)
    Result is expected to be completed with app-specific data (in app_details field)
    :param line: line of log
    :param logformat: regular expression pattern to use
    :return:
    """
    m = re.match(log_format_regex, line)
    if not m:
        return None
    m_dict = m.groupdict()

    # Clean non defined values
    for k, v in m_dict.items():
        if v == "-":
            m_dict[k] = None

    ts = dateutil_parser.parse(m_dict["timestamp"].replace(':', ' ', 1))
    common_data = {
        "timestamptz": ts.isoformat(),
        "username": _get_user_info(m_dict.get("user", ""))["name"],
        "org": _get_user_info(m_dict.get("user", ""))["org"],
        "roles": _get_user_info(m_dict.get("user", ""))["roles"],
        "request_path": m_dict.get("path", ""),
        "request_type": m_dict.get("method", ""),
        "user_agent": m_dict.get("user_agent", ""),
        "app_name": m_dict.get("app", ""),
        "app_details": None,
        "response_time": _int_or_none(m_dict.get("response_time")),
        "response_size": _int_or_none(m_dict.get("response_size")),
        "status_code": _int_or_none(m_dict.get("status_code", "")),
    }
    return common_data


def _to_csv(processed_log_entries, csv_filename: str = None) -> str:
    """
    Write the processed log entries into a CSV file
    :param processed_log_entries:
    :param csv_filename:
    :return:
    """
    field_names = list(processed_log_entries[0].keys())
    if not csv_filename:
        csv_filename = f"/tmp/{uuid4()}.csv"
    with open(csv_filename, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()
        writer.writerows(processed_log_entries)
    return csv_filename



def _get_user_info(user_string: str) -> dict:
    """
    The user information will be in a single |-separated string. Extract this info
    and store it in a structured way
    :param user_string: expecting something like testadmin|Project Steering Committee|ROLE_SUPERUSER,ROLE_MAPSTORE_ADMIN
    :return: dict {"name": thename, "org": theorg, "roles": the roles}
    """
    user_categories = ["name", "org", "roles"]
    user_values = [None, None, None]
    if user_string:
        user_values = user_string.split("|")
    user_info = dict(zip(user_categories, user_values))
    return user_info


def _read_request_line(request_line: str) -> tuple[str, str, str]:
    """
    Read the request_line string, extract request type, path and app id
    :param request_line: expecting something like "GET /geoserver/openlayers3/ol.css HTTP/1.1"
    :return: tuple (type, path, app) e.g. ("GET", "/geoserver/openlayers3/ol.css", "geoserver")
    """
    regex = "(GET|POST|HEAD|OPTION|PUT|PATCH|DELETE|TRACE|CONNECT) (https?:\/\/[_:a-zA-Z0-9\.-]+)?(\/([_a-zA-Z0-9-]+)(\/.*)) HTTP.*"
    try:
        matches = re.search(regex, request_line)
        return (matches[1], matches[3], matches[4])
    except:
        logging.warning(f'Could not parse request line {request_line}')
        return ("", "", "")


def _int_or_none(val: str):
    return int(val) if val else None