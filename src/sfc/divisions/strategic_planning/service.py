"""Strategic Planning Division — main service implementation."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from sfc.core.models import Division, ExecutionPlan, Platform, Priority, TaskType
from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.divisions.strategic_planning.interface import StrategicPlanningDivisionInterface
from sfc.divisions.strategic_planning.models import StrategicPlanningOutput
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, PlanningCycleCompleted, PlanningCycleStarted
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.strategic_planning.service")

_QUARTERLY_OBJECTIVES = [
    "Grow TikTok audience to 500K followers",
    "Achieve 5% average engagement rate across all platforms",
    "Launch 2 brand partnerships per quarter",
    "Cover all 18 SPL clubs with weekly content",
]

_TASK_TYPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "news": {
        "divisions_required": ["intelligence", "editorial", "governance", "publishing"],
        "platforms": ["tiktok", "x", "instagram_feed"],
        "content_types": ["breaking_news_article", "social_post"],
        "kpi": {"reach": 100000, "engagement_rate": 0.05},
    },
    "transfer": {
        "divisions_required": ["intelligence", "editorial", "creative", "governance", "publishing"],
        "platforms": ["tiktok", "instagram_reels", "x", "youtube_shorts"],
        "content_types": ["short_video", "analysis_thread"],
        "kpi": {"reach": 500000, "engagement_rate": 0.08},
    },
    "match": {
        "divisions_required": ["intelligence", "editorial", "creative", "governance", "publishing"],
        "platforms": ["tiktok", "instagram_reels", "x", "youtube"],
        "content_types": ["highlight_clip", "match_report", "tactical_analysis"],
        "kpi": {"reach": 300000, "engagement_rate": 0.06},
    },
    "crisis": {
        "divisions_required": ["intelligence", "governance", "editorial", "publishing"],
        "platforms": ["x", "telegram", "website"],
        "content_types": ["crisis_statement", "clarification_post"],
        "kpi": {"reach": 200000},
        "priority": "critical",
    },
    "campaign": {
        "divisions_required": ["intelligence", "editorial", "creative", "revenue", "governance", "publishing"],
        "platforms": ["tiktok", "instagram_reels", "youtube", "x", "telegram"],
        "content_types": ["campaign_hero_video", "social_post", "newsletter_edition"],
        "kpi": {"reach": 1000000, "revenue_usd": 50000},
    },
}


class StrategicPlanningService(StrategicPlanningDivisionInterface):
    """Strategic Planning Division — converts vision into executable plans."""

    division = Division.STRATEGIC_PLANNING

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0

    async def initialize(self) -> None:
        logger.info("[StrategicPlanning] Initialized")

    async def shutdown(self) -> None:
        logger.info("[StrategicPlanning] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            task_type = input.task_type
            payload = input.payload
            state = input.state_snapshot

            events: list[BaseEvent] = [
                PlanningCycleStarted(
                    division=self.division.value,
                    run_id=input.run_id,
                    payload={"task_type": task_type},
                )
            ]
            get_event_bus().publish_many(events)

            # Build execution plan
            defaults = _TASK_TYPE_DEFAULTS.get(task_type, _TASK_TYPE_DEFAULTS["news"])
            priority_str = defaults.get("priority", "high")
            priority = Priority(priority_str) if priority_str in [p.value for p in Priority] else Priority.HIGH

            try:
                task_type_enum = TaskType(task_type)
            except ValueError:
                task_type_enum = TaskType.NEWS

            plan = ExecutionPlan(
                task_type=task_type_enum,
                priority=priority,
                divisions_required=[Division(d) for d in defaults["divisions_required"] if d in [div.value for div in Division]],
                platforms_targeted=[Platform(p) for p in defaults["platforms"] if p in [pl.value for pl in Platform]],
                content_types=defaults["content_types"],
                kpi_targets=defaults.get("kpi", {}),
                parallel_tasks=["intelligence", "analytics_background", "revenue_background"],
                sequential_tasks=["editorial", "creative", "governance", "publishing"],
                estimated_duration_minutes=30,
            )

            plan_dict = plan.model_dump(mode="json")
            weekly_missions = await self.create_weekly_mission({
                "task_type": task_type,
                "objectives": _QUARTERLY_OBJECTIVES,
            })

            prioritized = await self.prioritize(
                payload.get("items", [{"name": task_type, "impact": 8, "confidence": 7, "ease": 6}])
            )

            if self.memory:
                self.memory.set(f"plan_{input.run_id}", plan_dict)

            completion_event = PlanningCycleCompleted(
                division=self.division.value,
                run_id=input.run_id,
                payload={"plan_id": str(plan.plan_id), "task_type": task_type},
            )
            get_event_bus().publish(completion_event)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return StrategicPlanningOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={
                    "execution_plan": plan_dict,
                    "weekly_missions": weekly_missions,
                    "prioritized_items": prioritized,
                    "pipeline_stage": "planning_complete",
                },
                events_to_publish=[*events, completion_event],
                processing_time_ms=elapsed,
                execution_plan=plan_dict,
                weekly_missions=weekly_missions,
                prioritized_items=prioritized,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[StrategicPlanning] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def create_annual_plan(self, vision: str, budget: float) -> dict[str, Any]:
        """Build a structured annual plan with Q1-Q4 milestones."""
        return {
            "plan_id": str(uuid.uuid4()),
            "vision": vision,
            "budget_usd": budget,
            "year": datetime.utcnow().year,
            "quarterly_milestones": {
                "Q1": {"focus": "Audience foundation", "target_followers": 100000},
                "Q2": {"focus": "Engagement growth", "target_engagement_rate": 0.05},
                "Q3": {"focus": "Revenue activation", "target_revenue_usd": budget * 0.3},
                "Q4": {"focus": "Scale and optimize", "target_followers": 500000},
            },
            "created_at": datetime.utcnow().isoformat(),
        }

    async def create_weekly_mission(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate 5 daily missions aligned to quarterly objectives."""
        task_type = context.get("task_type", "news")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        missions: list[dict[str, Any]] = []
        for i, day in enumerate(days):
            missions.append({
                "day": day,
                "mission": f"Day {i+1}: Cover {task_type} content across priority platforms",
                "objective": _QUARTERLY_OBJECTIVES[i % len(_QUARTERLY_OBJECTIVES)],
                "content_count_target": 3,
                "platforms": ["tiktok", "x", "instagram_feed"],
            })
        return missions

    async def prioritize(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank items by ICE score (Impact × Confidence × Ease)."""
        scored: list[dict[str, Any]] = []
        for item in items:
            impact = float(item.get("impact", 5))
            confidence = float(item.get("confidence", 5))
            ease = float(item.get("ease", 5))
            ice_score = impact * confidence * ease
            scored.append({**item, "ice_score": round(ice_score, 2)})
        scored.sort(key=lambda x: x["ice_score"], reverse=True)
        return scored

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.strategic_planning.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        reasons: list[str] = []
        if not content.get("task_type"):
            reasons.append("Missing task_type")
        return ValidationResult(valid=len(reasons) == 0, score=100.0 - len(reasons) * 20.0, reasons=reasons)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={"total_calls": self._call_count, "error_count": self._error_count},
            highlights=[f"{self._call_count} planning cycles executed"],
            recommendations=["Review quarterly milestones against actual KPIs monthly"],
        )

    def health_check(self) -> DivisionHealth:
        return DivisionHealth(
            division=self.division.value,
            status="healthy",
            metrics={"call_count": self._call_count, "error_count": self._error_count},
        )

    def describe(self) -> str:
        return "Vision to execution planning — annual, quarterly, weekly, daily"
