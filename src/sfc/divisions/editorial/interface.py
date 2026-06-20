"""Editorial Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class EditorialDivisionInterface(DivisionInterface):
    """Extended interface for the Editorial division."""

    @abstractmethod
    async def create_content_brief(
        self, intelligence_report: dict[str, Any], plan: dict[str, Any]
    ) -> dict[str, Any]:
        """Produce a structured editorial brief from an intelligence report."""
        ...

    @abstractmethod
    async def generate_draft(
        self, brief: dict[str, Any], content_type: str
    ) -> dict[str, Any]:
        """Generate a full content draft from a brief."""
        ...

    @abstractmethod
    async def check_accuracy_rules(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Validate the draft: no clickbait, no unsupported claims."""
        ...
