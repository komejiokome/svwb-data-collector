from __future__ import annotations

import abc

from svwb_collector.http_client import CachedHTTPClient
from svwb_collector.models import ConnectorResult


class BaseConnector(abc.ABC):
    source_key: str
    source_name: str
    is_official: bool

    def __init__(self, client: CachedHTTPClient) -> None:
        self.client = client

    @abc.abstractmethod
    def fetch(self) -> ConnectorResult:
        raise NotImplementedError
