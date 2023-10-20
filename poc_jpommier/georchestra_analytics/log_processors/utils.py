
from apachelogs import LogEntry
from datetime import datetime
import json
import logging
import re


def path_from_url(url: str):
    # url = logentry.request_line.split(" ")[1]
    regex = "(http|https)://[a-zA-Z0-9:-_]*/[a-zA-Z0-9:-_]*(.*)"
    try:
        matches = re.search(regex, url)
        return matches[2]
    except:
        logging.warning(f'Could not extract app path from URL {url}')
        return ''


def logentry_to_flat_dict(logentry: LogEntry):
    """
    Transform an apachelogs entry into a simpler, plain dict
    :param logentry: apachelogs entry (https://pypi.org/project/apachelogs/)
    :return: dict
    """
    blacklisted_keys = ["entry", "directives", "headers_in", "notes", "format"]
    log_dict = {k: v for k,v in logentry.__dict__.items() if k not in blacklisted_keys}
    # Move entries from the notes sub-dict to root dict
    log_dict = log_dict | logentry.notes
    return log_dict



class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)