"""
Generic log processor. Serves for simple cases or as fallback on apps for which a log processor has not yet
been created.
For now, does filter nothing.
"""

from typing import Any

from .abstract import AbstractLogProcessor


class GenericLogProcessor(AbstractLogProcessor):
    def __init__(
        self, app_path: str = "", app_id: str = "", config: dict[str, Any] = {}
    ):
        pass

    def collect_information_from_url(self, url: str) -> dict:
        return dict()

    def collect_information(
        self, request_path: str, url_params: dict[str, Any]
    ) -> dict:
        return dict()

    def is_relevant(self, path: str, query_string: str) -> bool:
        """We cannot define a generic validation logic => keep all !"""
        return True
