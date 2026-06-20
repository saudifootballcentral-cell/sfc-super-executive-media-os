"""Analytics Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class AnalyticsDivisionInterface(DivisionInterface):
    @abstractmethod
    async def calculate_performance_score(
        self, reach: int, engagement: float, target_reach: int
    ) -> float: ...

    @abstractmethod
    async def generate_recommendations(
        self, performance: dict[str, Any], benchmarks: dict[str, Any]
    ) -> list[str]: ...

    @abstractmethod
    async def identify_top_performing_patterns(
        self, history: list[dict[str, Any]]
    ) -> list[str]: ...
