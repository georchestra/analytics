"""
Abstract log processor. Defines an interface to be followed when implementing log processor classes
"""

from abc import ABC, abstractmethod


class AbstractLogProcessor(ABC):

    @staticmethod
    @abstractmethod
    def collect_information(url: str) -> dict:
        """
        Collect the app-specific information and structure it in a dict
        :param url:
        :return:
        """
        pass

    @staticmethod
    @abstractmethod
    def is_relevant(path: str) -> bool:
        """
        Determine whether a log line should be processed or dropped
        :param path: a URL, but with or without the http(s)://domain.name part
        :return:
        """
        pass
