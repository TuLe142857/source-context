from abc import ABC, abstractmethod
from typing import Literal

API_KIND = Literal["rest", "sse", "websocket"]

class ApiHandler(ABC):
    def __init__(self, kind: API_KIND):
        self._kind = kind

    @property
    def kind(self) -> str:
        return self._kind

    @abstractmethod
    def detect_api(self):
        pass

    @abstractmethod
    def match_api(self, api_endpoint, api_call) -> float:
        """ Return confident when matching 2 api. range [0, 100]"""
        pass