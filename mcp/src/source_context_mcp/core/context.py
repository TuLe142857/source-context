from dataclasses import dataclass

from .api_client import ApiClient
from .settings import Settings


@dataclass
class AppContext:
    api_client: ApiClient
    settings: Settings
