"""Intelligence Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class IntelligenceDivisionInterface(DivisionInterface):
    """Extended interface for the Intelligence division."""

    @abstractmethod
    async def gather_intelligence(
        self, topic: str, sources: list[str]
    ) -> dict[str, Any]:
        """Gather and structure intelligence for a topic from the given sources."""
        ...

    @abstractmethod
    async def verify_sources(
        self, claim: str, sources: list[str]
    ) -> dict[str, Any]:
        """Verify a claim against provided sources. Returns confidence score."""
        ...

    @abstractmethod
    async def classify_rumor(self, content: str) -> dict[str, Any]:
        """Classify whether content is a rumor, unverified, or confirmed fact."""
        ...

    @abstractmethod
    async def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract players, clubs, competitions, coaches from text."""
        ...

    @abstractmethod
    async def detect_trends(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect trending topics relevant to Saudi football."""
        ...
