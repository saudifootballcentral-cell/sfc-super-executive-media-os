"""Abstract base class for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sfc.ai.models import ModelRequest, ModelResponse


class AIProvider(ABC):
    """Abstract base for all AI providers."""

    @abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Complete an AI request and return a ModelResponse."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider has the required API key configured."""
        ...

    @abstractmethod
    def health_check(self) -> dict:
        """Return a health status dict for this provider."""
        ...
