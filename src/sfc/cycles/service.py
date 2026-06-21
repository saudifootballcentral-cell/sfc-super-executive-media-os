"""Operating Cycles Service — executes daily, weekly, monthly, quarterly, and annual cycles.

Each cycle runs a defined sequence of steps:
  Daily:     opportunity_scan → trend_scan → executive_brief → cost_check → memory_update
  Weekly:    performance_review → persona_review → growth_review → war_room_review
  Monthly:   strategy_review → revenue_review → sponsor_review → governance_review
  Quarterly: executive_planning → expansion_planning → platform_review
  Annual:    annual_report → strategic_reset → roadmap_planning
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from sfc.cycles.models import CyclePhase, CycleResult, CycleStep, CycleType

logger = logging.getLogger("sfc.cycles.service")


class CycleService:
    """Runs all five operating cycle types with full step tracking."""

    def __init__(self) -> None:
        self._history: list[CycleResult] = []
        self._executive_report_service: Any = None
        self._operational_report_service: Any = None
        self._historical_service: Any = None
        self._forecast_service: Any = None
        self._delivery_service: Any = None

    def inject_services(
        self,
        executive: Any = None,
        operational: Any = None,
        historical: Any = None,
        forecast: Any = None,
        delivery: Any = None,
    ) -> None:
        self._executive_report_service = executive
        self._operational_report_service = operational
        self._historical_service = historical
        self._forecast_service = forecast
        self._delivery_service = delivery

    async def run_daily(self, context: dict[str, Any] | None = None) -> CycleResult:
        """Daily cycle: opportunity scan → trend scan → executive brief → cost check → memory update."""
        return await self._run_cycle(
            CycleType.DAILY,
            [
                ("opportunity_scan", self._step_opportunity_scan),
                ("trend_scan", self._step_trend_scan),
                ("executive_brief", self._step_executive_brief),
                ("cost_check", self._step_cost_check),
                ("memory_update", self._step_memory_update),
            ],
            context or {},
        )

    async def run_weekly(self, context: dict[str, Any] | None = None) -> CycleResult:
        """Weekly cycle: performance review → persona review → growth review → war room review."""
        return await self._run_cycle(
            CycleType.WEEKLY,
            [
                ("performance_review", self._step_performance_review),
                ("persona_review", self._step_persona_review),
                ("growth_review", self._step_growth_review),
                ("war_room_review", self._step_war_room_review),
            ],
            context or {},
        )

    async def run_monthly(self, context: dict[str, Any] | None = None) -> CycleResult:
        """Monthly cycle: strategy → revenue → sponsor → governance reviews."""
        return await self._run_cycle(
            CycleType.MONTHLY,
            [
                ("strategy_review", self._step_strategy_review),
                ("revenue_review", self._step_revenue_review),
                ("sponsor_review", self._step_sponsor_review),
                ("governance_review", self._step_governance_review),
            ],
            context or {},
        )

    async def run_quarterly(self, context: dict[str, Any] | None = None) -> CycleResult:
        """Quarterly cycle: executive planning → expansion planning → platform review."""
        return await self._run_cycle(
            CycleType.QUARTERLY,
            [
                ("executive_planning", self._step_executive_planning),
                ("expansion_planning", self._step_expansion_planning),
                ("platform_review", self._step_platform_review),
            ],
            context or {},
        )

    async def run_annual(self, context: dict[str, Any] | None = None) -> CycleResult:
        """Annual cycle: annual report → strategic reset → roadmap planning."""
        return await self._run_cycle(
            CycleType.ANNUAL,
            [
                ("annual_report", self._step_annual_report),
                ("strategic_reset", self._step_strategic_reset),
                ("roadmap_planning", self._step_roadmap_planning),
            ],
            context or {},
        )

    def get_history(
        self, cycle_type: CycleType | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        results = self._history
        if cycle_type:
            results = [r for r in results if r.cycle_type == cycle_type]
        return [r.to_dict() for r in results[-limit:]]

    def get_summary(self) -> dict[str, Any]:
        total = len(self._history)
        by_type: dict[str, int] = {}
        for r in self._history:
            by_type[r.cycle_type.value] = by_type.get(r.cycle_type.value, 0) + 1
        return {
            "total_cycles_run": total,
            "by_type": by_type,
            "recent": [r.to_summary() for r in self._history[-5:]],
        }

    # ------------------------------------------------------------------
    # Core cycle runner
    # ------------------------------------------------------------------

    async def _run_cycle(
        self,
        cycle_type: CycleType,
        steps: list[tuple[str, Any]],
        context: dict[str, Any],
    ) -> CycleResult:
        t0 = time.perf_counter()
        logger.info("[CycleService] Starting %s cycle", cycle_type.value)
        result = CycleResult(cycle_type=cycle_type, status=CyclePhase.RUNNING)
        shared: dict[str, Any] = dict(context)

        for step_name, step_fn in steps:
            step = CycleStep(step_name=step_name, started_at=datetime.utcnow())
            ts = time.perf_counter()
            try:
                step_result = await step_fn(shared)
                if isinstance(step_result, dict):
                    shared.update(step_result)
                step.result = step_result if isinstance(step_result, dict) else {}
                step.status = CyclePhase.COMPLETED
                logger.debug("[CycleService] Step %s completed", step_name)
            except Exception as exc:
                logger.warning("[CycleService] Step %s failed (non-fatal): %s", step_name, exc)
                step.status = CyclePhase.FAILED
                step.error = str(exc)
                result.errors.append(f"{step_name}: {exc}")
            finally:
                step.completed_at = datetime.utcnow()
                step.duration_ms = int((time.perf_counter() - ts) * 1000)
                result.steps.append(step)

        result.status = (
            CyclePhase.COMPLETED
            if not result.errors
            else (CyclePhase.PARTIAL if len(result.errors) < len(steps) else CyclePhase.FAILED)
        )
        result.completed_at = datetime.utcnow()
        result.duration_ms = int((time.perf_counter() - t0) * 1000)
        result.executive_report = shared.get("executive_report", {})
        result.cost_forecast = shared.get("cost_forecast", {})
        result.historical_analytics = shared.get("historical_analytics", {})
        result.lessons_captured = shared.get("lessons_captured", [])

        self._history.append(result)
        if len(self._history) > 200:
            self._history = self._history[-200:]

        logger.info(
            "[CycleService] %s cycle %s in %dms | errors=%d",
            cycle_type.value,
            result.status.value,
            result.duration_ms,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    async def _step_opportunity_scan(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"opportunity_scan": {"status": "completed", "opportunities_found": 0}}

    async def _step_trend_scan(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._historical_service:
            growth = self._historical_service.get_growth_report()
            return {"trend_scan": growth, "historical_analytics": growth}
        return {"trend_scan": {"status": "no_historical_service"}}

    async def _step_executive_brief(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._executive_report_service:
            report = await self._executive_report_service.generate_daily_brief(ctx)
            return {"executive_report": report.to_dict()}
        return {"executive_report": {"status": "no_exec_service"}}

    async def _step_cost_check(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._forecast_service:
            forecast = self._forecast_service.forecast()
            return {"cost_forecast": forecast.to_dict()}
        return {"cost_forecast": {"status": "no_forecast_service"}}

    async def _step_memory_update(self, ctx: dict[str, Any]) -> dict[str, Any]:
        lessons = ctx.get("lessons_captured", [])
        return {"memory_update": {"lessons_stored": len(lessons)}}

    async def _step_performance_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._operational_report_service:
            report = await self._operational_report_service.generate_analytics_report(ctx)
            return {"performance_review": report.to_dict()}
        return {"performance_review": {"status": "no_operational_service"}}

    async def _step_persona_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._operational_report_service:
            report = await self._operational_report_service.generate_persona_report(ctx)
            return {"persona_review": report.to_dict()}
        return {"persona_review": {"status": "no_operational_service"}}

    async def _step_growth_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._historical_service:
            return {"growth_review": self._historical_service.get_growth_report()}
        return {"growth_review": {"status": "no_historical_service"}}

    async def _step_war_room_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._operational_report_service:
            report = await self._operational_report_service.generate_war_room_report(ctx)
            return {"war_room_review": report.to_dict()}
        return {"war_room_review": {"status": "no_operational_service"}}

    async def _step_strategy_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._executive_report_service:
            report = await self._executive_report_service.generate_monthly_review(ctx)
            return {"strategy_review": report.to_dict(), "executive_report": report.to_dict()}
        return {"strategy_review": {"status": "no_exec_service"}}

    async def _step_revenue_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._operational_report_service:
            report = await self._operational_report_service.generate_revenue_report(ctx)
            return {"revenue_review": report.to_dict()}
        return {"revenue_review": {"status": "no_operational_service"}}

    async def _step_sponsor_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        analytics = ctx.get("analytics_report", {})
        revenue = analytics.get("revenue_summary", {})
        return {
            "sponsor_review": {
                "high_value_signals": revenue.get("high_value_signals", 0),
                "priority_brand": revenue.get("priority_brand"),
                "total_opportunity_usd": revenue.get("total_opportunity_usd", 0),
            }
        }

    async def _step_governance_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._operational_report_service:
            report = await self._operational_report_service.generate_governance_report(ctx)
            return {"governance_review": report.to_dict()}
        return {"governance_review": {"status": "no_operational_service"}}

    async def _step_executive_planning(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._executive_report_service:
            report = await self._executive_report_service.generate_quarterly_review(ctx)
            return {"executive_planning": report.to_dict(), "executive_report": report.to_dict()}
        return {"executive_planning": {"status": "no_exec_service"}}

    async def _step_expansion_planning(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "expansion_planning": {
                "status": "completed",
                "recommendations": [
                    "Evaluate new platform integrations",
                    "Review persona coverage gaps",
                    "Assess war room upgrade requirements",
                ],
            }
        }

    async def _step_platform_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._operational_report_service:
            report = await self._operational_report_service.generate_platform_report(ctx)
            return {"platform_review": report.to_dict()}
        return {"platform_review": {"status": "no_operational_service"}}

    async def _step_annual_report(self, ctx: dict[str, Any]) -> dict[str, Any]:
        if self._executive_report_service:
            report = await self._executive_report_service.generate_annual_summary(ctx)
            return {"annual_report": report.to_dict(), "executive_report": report.to_dict()}
        return {"annual_report": {"status": "no_exec_service"}}

    async def _step_strategic_reset(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "strategic_reset": {
                "status": "completed",
                "lessons_captured": ctx.get("lessons_captured", []),
            }
        }

    async def _step_roadmap_planning(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "roadmap_planning": {
                "status": "completed",
                "next_packages": ["Package 9: SaaS Expansion", "Package 10: Real API Integrations"],
                "strategic_priorities": [
                    "Autonomous operations maturity",
                    "Revenue activation pipeline",
                    "Multi-tenant architecture",
                ],
            }
        }
