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
# import pytz
from datetime import datetime


from .utils import path_from_url

# Default log format string, you can provide a custom one with the option --logformat
logformat_default = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" - \"%{app}n\" \"-\" %{ms}Tms"
# logformat_default = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms"
page_size = 1000


def to_csv(processed_log_entries):
    field_names = list(processed_log_entries[0].keys())
    csv_filename = f"/tmp/{uuid4()}.csv"
    with open(csv_filename, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()
        writer.writerows(processed_log_entries)
    return csv_filename


def process_log_file(log_file_path: str, logformat: str = logformat_default):
    logparser = LogParser(logformat)
    with open(log_file_path, 'r') as logs_data:
        processed_log_entries = []
        for entry in logparser.parse_lines(logs_data):
            processed_log = process(entry)
            if (processed_log):
                processed_log["app_details"] = json.dumps(processed_log["app_details"])
                # processed_log["roles"] = ",".join(processed_log["roles"])
                processed_log_entries.append(processed_log)
        csv_filename = to_csv(processed_log_entries)
        return len(processed_log_entries), csv_filename

        # TODO Paginated publication


def get_user_info(user_string: str) -> str:
    user_categories = ["name", "org", "roles"]
    user_values = [None, None, None]
    if user_string is not None:
        user_values = user_string.split("|")
    user_info = dict(zip(user_categories, user_values))
    return user_info


def get_user(user_string: str) -> str:
    if not user_string:
        return None
    chunks = user_string.split("|")
    return chunks[0]


def get_org(user_string: str) -> str:
    if not user_string:
        return None
    chunks = user_string.split("|")
    if len(chunks) > 1:
        return chunks[1]
    else:
        return ""


def get_roles(user_string: str) -> list[str]:
    if not user_string:
        return None
    chunks = user_string.split("|")
    if len(chunks) > 2:
        return chunks[2].split(",")
    else:
        return ""


def read_request_line(request_line: str)-> tuple[str, str, str]:
    """
    Read the request_line string, extract request type, path and app id
    :param request_line:
    :return: tuple (type, path, app)
    """
    regex = "(GET|POST|HEAD|OPTION|PUT|PATCH|DELETE|TRACE|CONNECT) (https?:\/\/[_:a-zA-Z0-9\.-]+)?(\/([_a-zA-Z0-9-]+)(\/.*)) HTTP.*"
    try:
        matches = re.search(regex, request_line)
        return (matches[1], matches[3], matches[4])
    except:
        logging.warning(f'Could not parse request line {request_line}')
        return ("", "", "")


def collect_common_data(logentry):
    common_data = {
        "timestamptz":  logentry.request_time.isoformat(),
        "username": get_user_info(logentry.remote_user)["name"],
        "org": get_user_info(logentry.remote_user)["org"],
        "roles": get_user_info(logentry.remote_user)["roles"],
        "request_path": read_request_line(logentry.request_line)[1],
        "request_type": read_request_line(logentry.request_line)[0],
        "user_agent": logentry.headers_in["User-Agent"],
        "app_name": read_request_line(logentry.request_line)[2],
        "app_details": None,
        "response_time": logentry.request_duration_milliseconds,
        "response_size": logentry.bytes_sent,
        "http_code": logentry.final_status,
    }
    return common_data


def process(logentry: LogEntry):
    http_method, path, app = read_request_line(logentry.request_line)

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
