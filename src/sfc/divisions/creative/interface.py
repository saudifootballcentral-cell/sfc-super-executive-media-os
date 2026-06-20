"""Creative Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class CreativeDivisionInterface(DivisionInterface):
    @abstractmethod
    async def create_asset_brief(
        self, content_draft: dict[str, Any], platforms: list[str]
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def assign_producer(self, asset_type: str) -> str: ...

    @abstractmethod
    async def calculate_production_time(self, assets: list[dict[str, Any]]) -> float: ...
