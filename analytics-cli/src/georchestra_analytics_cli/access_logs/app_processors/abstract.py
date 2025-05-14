"""
Abstract log processor. Defines an interface to be followed when implementing log processor classes
"""

from abc import ABC, abstractmethod
from typing import Any


class AbstractLogProcessor(ABC):

    @abstractmethod
    def __init__(self, app_path: str = "", config: dict[str:Any] = {}):
        pass

    @abstractmethod
    def collect_information_from_url(self, url: str) -> dict:
        """
        Collect the app-specific information and structure it in a dict
        :param url: the request url
        :return:
        """
        pass

    @abstractmethod
    def collect_information(self, request_path: str, url_params: dict[str, Any]) -> dict:
        """
        Collect the app-specific information and structure it in a dict.
        Takes as input an already split URL: path and params
        :param request_path:
        :param url_params:
        :return:
        """
        pass

    @abstractmethod
    def is_relevant(self, path: str, query_string: str) -> bool:
        """
        Determine whether a log line should be processed or dropped
        :param path: a URL, but with or without the http(s)://domain.name part
        :return:
        """
        pass
