"""Strategic Planning Division stub — Package 2 will implement goal setting and roadmaps."""

from __future__ import annotations

from typing import Any

from sfc.core.models import Division
from sfc.divisions.base import DivisionInterface
from sfc.graph.state import SFCState


class StrategicPlanningDivision(DivisionInterface):
    """Strategic Planning Division.

    Package 2 implementation will include:
    - Quarterly KPI target setting
    - Campaign roadmap management
    - Competitive landscape tracking
    - Market share / share of voice goals
    - Budget allocation across divisions
    - Platform growth strategy
    - Content calendar management
    - World Cup 2034 content strategy
    - Saudi Pro League season content arcs
    """

    division = Division.STRATEGIC_PLANNING

    async def process(self, state: SFCState) -> dict[str, Any]:
        raise NotImplementedError("Strategic Planning Division not yet implemented — Package 2")

    def health_check(self) -> dict[str, Any]:
        return {"division": self.division, "status": "stub", "package": 2}

    def describe(self) -> str:
        return "Goals, roadmaps, campaigns, and quarterly strategy"

    async def get_active_campaigns(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def get_quarterly_goals(self, quarter: str) -> dict[str, Any]:
        raise NotImplementedError

    async def align_with_strategy(self, task: dict[str, Any]) -> dict[str, Any]:
        """Check if a task aligns with current strategic goals."""
        raise NotImplementedError
