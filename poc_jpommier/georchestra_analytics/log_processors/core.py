"""
Core log processing functions
- handle apache CLF logs files, extract common information
- call application-logic modules to extract information that is specific to each app
"""

import importlib
import logging
from apachelogs import LogParser, LogEntry

from georchestra_analytics.log_processors import path_from_url

# Default log format string, you can provide a custom one with the option --logformat
logformat_default = "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" - \"%{app}n\" \"-\" %{ms}Tms";


def process_log_file(log_file_path: str):
  logparser = LogParser(logformat_default)
  with open(log_file_path, 'r') as logs_data:
    processed_log_entries = []
    for entry in logparser.parse_lines(logs_data):
      processed_log = process(entry)
      if (processed_log):
        processed_log_entries.append(processed_log)

  print(processed_log_entries)


def get_user(user_string: str) -> str:
    chunks = user_string.split("|")
    return chunks[0]


def get_org(user_string: str) -> str:
    chunks = user_string.split("|")
    if len(chunks) > 1:
        return chunks[1]
    else:
        return ""


def get_roles(user_string: str) -> list[str]:
    chunks = user_string.split("|")
    if len(chunks) > 2:
        return chunks[2].split(",")
    else:
        return ""


def collect_common_data(logentry):
    common_data = {
        "timestamptz": logentry.request_time.isoformat(),
        "user": get_user(logentry.remote_user),
        "org": get_org(logentry.remote_user),
        "roles": get_roles(logentry.remote_user),
        "url": path_from_url(logentry.headers_in["Referer"]),
        "user_agent": logentry.headers_in["User-Agent"],
        "app_name": logentry.notes["app"],
        "app_details": None,
        "response_time": logentry.request_duration_milliseconds,
        "response_size": logentry.bytes_sent,
        "http_code": logentry.final_status,
    }
    return common_data


def process(logentry: LogEntry):
    # try:
    app = logentry.notes.get("app", "")
    logging.debug(f"processing log record for app {app}")
    url = logentry.headers_in['Referer']
    log_processor = importlib.import_module(f"georchestra_analytics.log_processors.{app}")
    if not log_processor.is_relevant(url):
      logging.debug(f"dropped {url}")
      return None
    logging.debug(f"keep    {url}")
    data = collect_common_data(logentry)
    custom_info = log_processor.collect_information(url)
    data["app_details"] = custom_info
    return data
    # except Exception as e:
    #     print(e)
    #     return None
