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

from apachelogs import LogParser, LogEntry
import logging
from uuid import uuid4

# Default log format string, you can provide a custom one with the option --logformat
logformat_default = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" - \"%{app}n\" \"-\" %{ms}Tms"
# logformat_default = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms"
page_size = 1000


def process_log_file(log_file_path: str, logformat: str = logformat_default) -> tuple[int, str]:
    """
    Take a log file, parse it using the defined parser format (default it logformat_default above)
    Filter and process the log lines
    Output the result into a CSV file
    :param log_file_path:
    :param logformat: defines the parsing logic. Ref. is https://httpd.apache.org/docs/2.4/logs.html
    :return: tuple (nb lines kept, csv file name)
    """
    logparser = LogParser(logformat)
    with open(log_file_path, 'r') as logs_data:
        processed_log_entries = []
        for entry in logparser.parse_lines(logs_data):
            processed_log = process(entry)
            if (processed_log):
                processed_log["app_details"] = json.dumps(processed_log["app_details"])
                # processed_log["roles"] = ",".join(processed_log["roles"])
                processed_log_entries.append(processed_log)
        csv_filename = _to_csv(processed_log_entries)
        return len(processed_log_entries), csv_filename
        # TODO Paginated publication


def process(logentry: LogEntry) -> dict:
    """
    Process a single log line:
    - determines which log processor class to use for filtering and extracting app-specific data
    - collect common data
    - merge it all
    :param logentry:
    :return: a dict containing all the gathered information. Or None if the line is filtered-out
    """
    http_method, path, app = _read_request_line(logentry.request_line)

    # logging.debug(f"processing log record for app {app}")

    log_processor = None
    # Next lines of code try to get the log processor class, implementation of AbstractLogProcessor, expected to be
    # provided by the package of the same name as the app (e.g. geoserver, geonetwork, mapstore etc)
    # If it doesn't find such a log processor class, it will fallback on a generic one.
    # Please do try to provide an app-specific one, since for now at least, the generic log processor does not filter any
    # line which might result in huge overhead for the storage database
    try:
        app_module = importlib.import_module(f"georchestra_analytics.log_processors.{app.lower()}")
        log_processor_class_ = getattr(app_module, f"{app.capitalize()}LogProcessor")
        log_processor = log_processor_class_()
    except ModuleNotFoundError as e:
        logging.warning(f"Log processor for app {app} not found. Falling back with generic log processor")
        log_processor = importlib.import_module(f"georchestra_analytics.log_processors.generic").GenericLogProcessor()

    # Filter out uninteresting lines (in regard to analytics needs)
    if not log_processor.is_relevant(path):
        logging.debug(f"dropped {path}")
        return None
    logging.debug(f"keep    {path}")
    data = collect_common_data(logentry)
    custom_info = log_processor.collect_information(path)
    data["app_details"] = custom_info
    return data


def collect_common_data(logentry):
    """
    For a single parsed log line, collect all the information that will be common to all kind of apps
    (mostly, collects the chunks in the log line but does not process the URL structure)
    Result is expected to be completed with app-specific data (in app_details field)
    :param logentry:
    :return:
    """
    common_data = {
        "timestamptz": logentry.request_time.isoformat(),
        "username": _get_user_info(logentry.remote_user)["name"],
        "org": _get_user_info(logentry.remote_user)["org"],
        "roles": _get_user_info(logentry.remote_user)["roles"],
        "request_path": _read_request_line(logentry.request_line)[1],
        "request_type": _read_request_line(logentry.request_line)[0],
        "user_agent": logentry.headers_in["User-Agent"],
        "app_name": _read_request_line(logentry.request_line)[2],
        "app_details": None,
        "response_time": logentry.request_duration_milliseconds,
        "response_size": logentry.bytes_sent,
        "http_code": logentry.final_status,
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
    if user_string is not None:
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
