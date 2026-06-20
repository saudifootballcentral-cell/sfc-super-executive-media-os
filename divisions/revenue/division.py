"""Revenue Division — tracks sponsors, partnership opportunities, and revenue."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from core.models import Division, EventType, SFCEvent
from divisions.base import BaseDivision


class RevenueDivision(BaseDivision):
    """Manages revenue streams and sponsor relationships.

    Responsibilities:
    - Sponsor discovery
    - Partnership tracking
    - Revenue forecasting
    - Campaign monetization
    """

    division = Division.REVENUE

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        if EventType(event.event_type) == EventType.SPONSOR_OPPORTUNITY_DETECTED:
            return await self._log_sponsor_opportunity(event)
        return None

    async def _log_sponsor_opportunity(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        opportunity_id = str(uuid4())
        record = {
            "opportunity_id": opportunity_id,
            "brand": payload.get("brand"),
            "category": payload.get("category"),
            "estimated_value_usd": payload.get("estimated_value_usd", 0.0),
            "contact": payload.get("contact"),
            "status": "identified",
            "detected_at": datetime.utcnow().isoformat(),
        }
        self.memory.set(f"sponsor:{opportunity_id}", record)
        self.logger.info("[Revenue] Sponsor opportunity: %s — $%.0f", record["brand"], record["estimated_value_usd"])
        return record

    def add_sponsor(
        self,
        brand: str,
        deal_value_usd: float,
        category: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        sponsor_id = str(uuid4())
        record = {
            "sponsor_id": sponsor_id,
            "brand": brand,
            "deal_value_usd": deal_value_usd,
            "category": category,
            "start_date": start_date,
            "end_date": end_date,
            "status": "active",
        }
        self.memory.set(f"sponsor_active:{sponsor_id}", record)
        self.logger.info("[Revenue] Active sponsor added: %s ($%.0f)", brand, deal_value_usd)
        return record

    def forecast_revenue(self, period_days: int = 90) -> dict[str, Any]:
        sponsor_keys = [k for k in self.memory.keys() if k.startswith("sponsor_active:")]
        sponsors = [self.memory.get(k) for k in sponsor_keys]
        total_annual = sum(s.get("deal_value_usd", 0.0) for s in sponsors)
        period_revenue = (total_annual / 365) * period_days

        return {
            "period_days": period_days,
            "active_sponsors": len(sponsors),
            "forecast_revenue_usd": period_revenue,
            "annualized_revenue_usd": total_annual,
        }

    def get_all_opportunities(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("sponsor:") and not k.startswith("sponsor_active:")
        ]

    def get_active_sponsors(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("sponsor_active:")
        ]
