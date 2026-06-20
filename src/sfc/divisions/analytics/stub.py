"""Analytics Division stub — Package 2 will implement real platform metrics APIs."""

from __future__ import annotations

from typing import Any

from sfc.core.models import Division
from sfc.divisions.base import DivisionInterface
from sfc.graph.state import SFCState


class AnalyticsDivision(DivisionInterface):
    """Analytics Division.

    Package 2 implementation will include:
    - TikTok Analytics API
    - Instagram Insights API
    - YouTube Analytics API
    - X (Twitter) Analytics API
    - Cross-platform reach, watch time, retention, engagement aggregation
    - Attribution modeling
    - A/B test tracking
    - Growth forecasting
    - Share of Voice calculation vs competitors
    - Revenue attribution
    - Content performance scoring
    """

    division = Division.ANALYTICS

    async def process(self, state: SFCState) -> dict[str, Any]:
        raise NotImplementedError("Analytics Division not yet implemented — Package 2")

    def health_check(self) -> dict[str, Any]:
        return {"division": self.division, "status": "stub", "package": 2}

    def describe(self) -> str:
        return "Performance measurement, growth analytics, and optimisation insights"

    async def background_analysis(self, state: SFCState) -> dict[str, Any]:
        """Parallel phase: analyse historical data while intelligence runs."""
        raise NotImplementedError

    async def final_report(self, state: SFCState) -> dict[str, Any]:
        """Join phase: produce final analytics report after publishing."""
        raise NotImplementedError

    async def get_platform_metrics(self, content_id: str, platform: str) -> dict[str, Any]:
        raise NotImplementedError

    async def calculate_share_of_voice(self, topic: str, competitor_handles: list[str]) -> float:
        raise NotImplementedError
