"""Base provider interface for Package 10A."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDataProvider(ABC):
    """Abstract base for all data providers."""

    @property
    @abstractmethod
    def data_source(self) -> str:
        """Unique identifier for this provider's data source."""

    @abstractmethod
    def is_available(self) -> bool:
        """True when real credentials are present and provider can be used."""

    @abstractmethod
    async def fetch(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch raw data records for a query. Returns fixture data if unavailable."""
