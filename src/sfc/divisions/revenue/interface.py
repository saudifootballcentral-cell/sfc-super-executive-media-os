"""Revenue Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class RevenueDivisionInterface(DivisionInterface):
    @abstractmethod
    async def score_opportunity(
        self, content: dict[str, Any], sponsor_categories: list[str]
    ) -> float: ...

    @abstractmethod
    async def create_campaign_concept(self, opportunity: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def forecast_revenue(
        self, signals: list[dict[str, Any]], platforms: list[str], duration_days: int
    ) -> dict[str, Any]: ...
