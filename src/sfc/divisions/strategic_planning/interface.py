"""Strategic Planning Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class StrategicPlanningDivisionInterface(DivisionInterface):
    @abstractmethod
    async def create_annual_plan(
        self, vision: str, budget: float
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def create_weekly_mission(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def prioritize(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
