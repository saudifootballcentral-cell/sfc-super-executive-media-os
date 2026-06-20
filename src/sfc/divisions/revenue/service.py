"""Revenue Division — main service implementation."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sfc.core.models import Division
from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.divisions.revenue.interface import RevenueDivisionInterface
from sfc.divisions.revenue.models import RevenueOutput
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, RevenueOpportunityDetected
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.revenue.service")

_CPM_RATES: dict[str, float] = {
    "tiktok": 2.5, "instagram_reels": 3.0, "youtube": 4.0,
    "x": 1.5, "telegram": 1.0, "website": 5.0, "newsletter": 8.0,
}

_SPONSOR_CATEGORIES = ["telecom", "finance", "fmcg", "sportswear", "automotive"]

_TASK_TYPE_SPONSOR_FIT: dict[str, list[str]] = {
    "transfer": ["sportswear", "finance"],
    "match": ["telecom", "fmcg", "sportswear"],
    "news": ["telecom", "fmcg"],
    "campaign": ["finance", "automotive"],
}


class RevenueService(RevenueDivisionInterface):
    """Revenue Division — monetization signals and sponsor opportunity scoring."""

    division = Division.REVENUE

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0

    async def initialize(self) -> None:
        logger.info("[Revenue] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Revenue] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            content_drafts = state.get("content_drafts", [])
            plan = state.get("execution_plan", {})
            platforms = plan.get("platforms_targeted", [])
            task_type = plan.get("task_type", input.task_type)

            sponsor_cats = _TASK_TYPE_SPONSOR_FIT.get(task_type, _SPONSOR_CATEGORIES[:2])
            signals: list[dict[str, Any]] = []
            events: list[BaseEvent] = []

            for draft in content_drafts:
                score = await self.score_opportunity(draft, sponsor_cats)
                if score >= 60.0:
                    concept = await self.create_campaign_concept({"content": draft, "score": score})
                    forecast = await self.forecast_revenue([{"score": score}], platforms, 30)
                    signal = {
                        "content_id": draft.get("content_id"),
                        "content_type": draft.get("content_type"),
                        "opportunity_score": score,
                        "sponsor_categories": sponsor_cats,
                        "campaign_concept": concept,
                        "estimated_value_usd": forecast.get("total_revenue_usd", 0),
                        "platforms": platforms,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                    signals.append(signal)
                    events.append(RevenueOpportunityDetected(
                        division=self.division.value,
                        run_id=input.run_id,
                        payload={"score": score, "estimated_value_usd": signal["estimated_value_usd"]},
                    ))

            if self.memory:
                self.memory.set(f"signals_{input.run_id}", signals)

            get_event_bus().publish_many(events)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return RevenueOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={"revenue_signals": signals, "pipeline_stage": "revenue_complete"},
                events_to_publish=events,
                processing_time_ms=elapsed,
                revenue_signals=signals,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Revenue] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def score_opportunity(
        self, content: dict[str, Any], sponsor_categories: list[str]
    ) -> float:
        """Score monetization opportunity 0-100."""
        base = 50.0
        brand_alignment = content.get("scores", {}).get("brand_alignment_score", 70.0)
        alignment_bonus = (brand_alignment - 70.0) * 0.5
        cat_bonus = min(len(sponsor_categories) * 5.0, 20.0)
        return round(min(100.0, base + alignment_bonus + cat_bonus), 2)

    async def create_campaign_concept(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Generate a sponsor activation brief."""
        content = opportunity.get("content", {})
        score = opportunity.get("score", 60.0)
        return {
            "campaign_type": "sponsored_content",
            "content_title": content.get("title", "Saudi Football Content"),
            "activation": "Pre-roll sponsorship + branded hashtag integration",
            "estimated_cpm_usd": 3.0,
            "opportunity_score": score,
            "duration_days": 7,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def forecast_revenue(
        self, signals: list[dict[str, Any]], platforms: list[str], duration_days: int
    ) -> dict[str, Any]:
        """Estimate revenue over duration."""
        avg_score = sum(s.get("score", 60) for s in signals) / max(len(signals), 1)
        platform_multiplier = sum(_CPM_RATES.get(p, 2.0) for p in platforms) / max(len(platforms), 1)
        base_revenue = (avg_score / 100) * platform_multiplier * duration_days * 100
        return {
            "total_revenue_usd": round(base_revenue, 2),
            "duration_days": duration_days,
            "platform_count": len(platforms),
            "avg_cpm_usd": round(platform_multiplier, 2),
            "forecasted_at": datetime.utcnow().isoformat(),
        }

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.revenue.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        reasons: list[str] = []
        if not content.get("content_id"):
            reasons.append("Missing content_id")
        return ValidationResult(valid=len(reasons) == 0, score=100.0 - len(reasons) * 20.0, reasons=reasons)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={"total_calls": self._call_count, "error_count": self._error_count},
            highlights=[f"{self._call_count} revenue analysis runs"],
            recommendations=["Develop direct sponsor relationships for premium CPM rates"],
        )

    def health_check(self) -> DivisionHealth:
        return DivisionHealth(
            division=self.division.value,
            status="healthy",
            metrics={"call_count": self._call_count, "error_count": self._error_count},
        )

    def describe(self) -> str:
        return "Monetization signals, sponsor opportunity scoring, revenue forecasting"
