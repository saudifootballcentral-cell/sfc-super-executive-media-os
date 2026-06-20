"""Publishing Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class PublishingDivisionInterface(DivisionInterface):
    @abstractmethod
    async def create_publishing_plan(
        self, approved_content: list[dict[str, Any]], plan: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def apply_platform_constraints(
        self, content: dict[str, Any], platform: str
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def estimate_optimal_time(self, platform: str, task_type: str) -> str: ...
