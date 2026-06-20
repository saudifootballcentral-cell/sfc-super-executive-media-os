"""Strategic Planning Division — sets goals, roadmaps, and campaign strategy."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from core.models import Division, EventType, SFCEvent
from divisions.base import BaseDivision


class StrategicPlanningDivision(BaseDivision):
    """Owns the company's strategic goals, quarterly roadmaps, and campaign planning.

    Responsibilities:
    - Define KPI targets
    - Build campaign roadmaps
    - Allocate division priorities
    - Track strategic initiative progress
    """

    division = Division.STRATEGIC_PLANNING

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        if EventType(event.event_type) == EventType.CAMPAIGN_STARTED:
            return await self._log_campaign(event)
        if EventType(event.event_type) == EventType.CAMPAIGN_COMPLETED:
            return await self._close_campaign(event)
        return None

    async def _log_campaign(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        campaign_id = payload.get("campaign_id", str(uuid4()))
        record = {
            "campaign_id": campaign_id,
            "name": payload.get("name", "Unnamed Campaign"),
            "objective": payload.get("objective"),
            "kpi_targets": payload.get("kpi_targets", {}),
            "platforms": payload.get("platforms", []),
            "start_date": datetime.utcnow().isoformat(),
            "status": "active",
        }
        self.memory.set(f"campaign:{campaign_id}", record)
        self.logger.info("[Strategic] Campaign started: %s", record["name"])
        return record

    async def _close_campaign(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        campaign_id = payload.get("campaign_id")
        record = self.memory.get(f"campaign:{campaign_id}", {})
        record["status"] = "completed"
        record["end_date"] = datetime.utcnow().isoformat()
        record["results"] = payload.get("results", {})
        self.memory.set(f"campaign:{campaign_id}", record)
        return record

    def set_quarterly_goal(self, quarter: str, metric: str, target: float) -> None:
        key = f"goal:{quarter}:{metric}"
        self.memory.set(key, {"quarter": quarter, "metric": metric, "target": target})
        self.logger.info("[Strategic] Goal set — %s %s: %.0f", quarter, metric, target)

    def get_active_campaigns(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("campaign:") and self.memory.get(k, {}).get("status") == "active"
        ]

    def get_quarterly_goals(self, quarter: str) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith(f"goal:{quarter}:")
        ]
