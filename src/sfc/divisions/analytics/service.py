"""Analytics Division — main service implementation."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sfc.core.models import Division
from sfc.divisions.analytics.interface import AnalyticsDivisionInterface
from sfc.divisions.analytics.models import AnalyticsOutput
from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, PerformanceUpdated
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.analytics.service")

_BENCHMARKS: dict[str, dict[str, Any]] = {
    "tiktok": {"avg_reach": 80000, "avg_engagement": 0.07},
    "instagram_reels": {"avg_reach": 45000, "avg_engagement": 0.05},
    "youtube": {"avg_reach": 30000, "avg_engagement": 0.04},
    "x": {"avg_reach": 20000, "avg_engagement": 0.03},
}


class AnalyticsService(AnalyticsDivisionInterface):
    """Analytics Division — performance measurement and optimisation."""

    division = Division.ANALYTICS

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0

    async def initialize(self) -> None:
        logger.info("[Analytics] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Analytics] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            publish_results = state.get("publish_results", {})
            background = state.get("analytics_background_data", {})
            revenue_signals = state.get("revenue_signals", [])
            plan = state.get("execution_plan", {})
            approved_content = state.get("approved_content", [])

            content_count = len(approved_content)
            task_type = plan.get("task_type", input.task_type)
            platforms = list(publish_results.get("platform_results", {}).keys())

            benchmarks = background.get("benchmarks", {})
            estimated_reach = self._estimate_reach(content_count, task_type)
            engagement_rate = self._estimate_engagement(task_type)
            perf_score = await self.calculate_performance_score(estimated_reach, engagement_rate, 50000)
            history = background.get("top_performing_content_patterns", [])
            patterns = await self.identify_top_performing_patterns(
                [{"pattern": p} for p in (history if isinstance(history, list) else [])]
            )
            recommendations = await self.generate_recommendations(
                {"reach": estimated_reach, "engagement_rate": engagement_rate},
                benchmarks,
            )

            report: dict[str, Any] = {
                "run_id": state.get("run_id", input.run_id),
                "content_pieces_published": content_count,
                "platforms_reached": platforms,
                "estimated_reach": estimated_reach,
                "estimated_engagement_rate": engagement_rate,
                "estimated_watch_time_minutes": content_count * 15,
                "performance_score": perf_score,
                "kpi_vs_target": self._compare_kpis(content_count, plan.get("kpi_targets", {}), task_type),
                "benchmark_comparison": benchmarks,
                "revenue_signal_count": len(revenue_signals),
                "estimated_revenue_impact_usd": sum(
                    s.get("estimated_value_usd", 0) for s in revenue_signals
                ),
                "top_performing_patterns": patterns,
                "optimisation_recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat(),
            }

            if self.memory:
                self.memory.set(f"analytics_{input.run_id}", report)

            events: list[BaseEvent] = [
                PerformanceUpdated(
                    division=self.division.value,
                    run_id=input.run_id,
                    payload={
                        "estimated_reach": estimated_reach,
                        "performance_score": perf_score,
                    },
                )
            ]
            get_event_bus().publish_many(events)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return AnalyticsOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={"analytics_report": report, "pipeline_stage": "analytics_complete"},
                events_to_publish=events,
                processing_time_ms=elapsed,
                analytics_report=report,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Analytics] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def calculate_performance_score(
        self, reach: int, engagement: float, target_reach: int
    ) -> float:
        if target_reach <= 0:
            return 50.0
        reach_ratio = min(reach / target_reach, 2.0)
        engagement_score = min(engagement * 1000, 10.0)
        score = (reach_ratio * 70 + engagement_score * 30) / 2
        return round(min(100.0, score), 2)

    async def generate_recommendations(
        self, performance: dict[str, Any], benchmarks: dict[str, Any]
    ) -> list[str]:
        recs: list[str] = []
        reach = performance.get("reach", 0)
        engagement = performance.get("engagement_rate", 0.0)

        tiktok_bench = benchmarks.get("tiktok", {}).get("avg_reach", 80000)
        if reach < tiktok_bench:
            recs.append("Increase TikTok posting frequency to boost reach above benchmark")
        if engagement < 0.05:
            recs.append("A/B test thumbnail styles — current engagement below 5% target")
        recs.append("Cross-post to Telegram within 5 minutes of primary platform publish")
        recs.append("Schedule posts at peak engagement times per platform")
        if len(recs) < 3:
            recs.append("Analyze top 10 performing pieces and replicate format")
        return recs[:5]

    async def identify_top_performing_patterns(
        self, history: list[dict[str, Any]]
    ) -> list[str]:
        if not history:
            return ["breaking_news_header", "player_reveal_video", "match_highlight_reel"]
        return [item.get("pattern", "standard_content") for item in history[:5]]

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.analytics.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        reasons: list[str] = []
        if "estimated_reach" not in content:
            reasons.append("Missing estimated_reach")
        return ValidationResult(valid=len(reasons) == 0, score=100.0 - len(reasons) * 20.0, reasons=reasons)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={"total_calls": self._call_count, "error_count": self._error_count},
            highlights=[f"{self._call_count} analytics reports generated"],
            recommendations=["Integrate real platform API metrics for production"],
        )

    def health_check(self) -> DivisionHealth:
        return DivisionHealth(
            division=self.division.value,
            status="healthy",
            metrics={"call_count": self._call_count, "error_count": self._error_count},
        )

    def describe(self) -> str:
        return "Performance measurement, benchmarking, and optimisation"

    def _estimate_reach(self, content_count: int, task_type: str) -> int:
        base = {"news": 50000, "match": 200000, "transfer": 500000, "crisis": 300000}.get(task_type, 30000)
        return base * max(content_count, 1)

    def _estimate_engagement(self, task_type: str) -> float:
        return {"transfer": 0.08, "match": 0.06, "news": 0.04, "trend": 0.07}.get(task_type, 0.04)

    def _compare_kpis(self, content_count: int, targets: dict[str, Any], task_type: str) -> dict[str, Any]:
        estimated_reach = self._estimate_reach(content_count, task_type)
        target_reach = targets.get("reach", targets.get("views", 10000))
        return {
            "reach_vs_target": f"{estimated_reach / target_reach * 100:.1f}%" if target_reach else "N/A",
            "on_track": estimated_reach >= target_reach if target_reach else True,
        }
