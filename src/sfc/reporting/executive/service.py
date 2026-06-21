"""Executive Report Service — generates all executive report types."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sfc.reporting.executive.models import (
    ExecutiveKPI,
    ExecutiveReport,
    ReportPeriod,
    ReportSection,
)

logger = logging.getLogger("sfc.reporting.executive.service")


class ExecutiveReportService:
    """Generates daily, weekly, monthly, quarterly, and annual executive reports."""

    def __init__(self) -> None:
        self._report_history: list[ExecutiveReport] = []

    async def generate_daily_brief(self, context: dict[str, Any]) -> ExecutiveReport:
        """Generate the daily executive brief."""
        return await self._generate(ReportPeriod.DAILY, context)

    async def generate_weekly_report(self, context: dict[str, Any]) -> ExecutiveReport:
        """Generate the weekly executive report."""
        return await self._generate(ReportPeriod.WEEKLY, context)

    async def generate_monthly_review(self, context: dict[str, Any]) -> ExecutiveReport:
        """Generate monthly performance review."""
        return await self._generate(ReportPeriod.MONTHLY, context)

    async def generate_quarterly_review(self, context: dict[str, Any]) -> ExecutiveReport:
        """Generate quarterly strategy review."""
        return await self._generate(ReportPeriod.QUARTERLY, context)

    async def generate_annual_summary(self, context: dict[str, Any]) -> ExecutiveReport:
        """Generate annual executive summary."""
        return await self._generate(ReportPeriod.ANNUAL, context)

    async def generate_dashboard_pack(self, context: dict[str, Any]) -> ExecutiveReport:
        """Generate executive dashboard data pack."""
        return await self._generate(ReportPeriod.DASHBOARD, context)

    def get_history(self, period: ReportPeriod | None = None) -> list[dict[str, Any]]:
        reports = self._report_history
        if period:
            reports = [r for r in reports if r.period == period]
        return [r.to_dict() for r in reports[-50:]]

    # ------------------------------------------------------------------
    # Core generation logic
    # ------------------------------------------------------------------

    async def _generate(self, period: ReportPeriod, context: dict[str, Any]) -> ExecutiveReport:
        logger.info("[ExecutiveReport] Generating %s report", period.value)

        analytics = context.get("analytics_report", {})
        revenue_summary = analytics.get("revenue_summary", {})
        cost_tracker_data = context.get("cost_summary", {})
        ai_metrics = context.get("ai_metrics", {})
        war_room_state = context.get("war_room_state", {})
        persona_outputs = context.get("persona_outputs", [])
        governance_reviews = context.get("governance_reviews", [])
        approved_content = context.get("approved_content", [])
        rejected_content = context.get("rejected_content", [])
        lessons = context.get("lessons_learned", [])

        kpis = self._build_kpis(analytics, revenue_summary, cost_tracker_data)
        wins, risks, opportunities = self._extract_insights(
            analytics, revenue_summary, governance_reviews, lessons
        )
        recommendations = self._build_recommendations(
            wins, risks, opportunities, cost_tracker_data
        )

        report = ExecutiveReport(
            period=period,
            period_start=self._period_start(period),
            period_end=datetime.utcnow(),
            executive_summary=self._build_summary(period, analytics, revenue_summary, approved_content),
            key_wins=wins,
            key_risks=risks,
            opportunities=opportunities,
            recommendations=recommendations,
            ai_usage=self._extract_ai_usage(ai_metrics, cost_tracker_data),
            cost_summary=cost_tracker_data,
            war_room_summary=self._extract_war_room_summary(war_room_state),
            persona_summary=self._extract_persona_summary(persona_outputs),
            revenue_summary=revenue_summary,
            governance_summary=self._extract_governance_summary(
                governance_reviews, approved_content, rejected_content
            ),
            kpis=kpis,
            content_published=len(approved_content),
            content_rejected=len(rejected_content),
            total_reach=analytics.get("estimated_reach", 0),
            total_revenue_opportunity_usd=float(revenue_summary.get("total_opportunity_usd", 0)),
        )

        # AI-enhanced executive summary
        report.ai_insights = await self._ai_insights(period, report)

        self._report_history.append(report)
        logger.info("[ExecutiveReport] %s report generated | id=%s", period.value, report.report_id)
        return report

    def _build_summary(
        self,
        period: ReportPeriod,
        analytics: dict[str, Any],
        revenue: dict[str, Any],
        approved: list[Any],
    ) -> str:
        reach = analytics.get("estimated_reach", 0)
        engagement = analytics.get("estimated_engagement_rate", 0)
        perf = analytics.get("performance_score", 0)
        total_opp = revenue.get("total_opportunity_usd", 0)
        priority_brand = revenue.get("priority_brand")
        period_label = period.value.capitalize()
        parts = [
            f"{period_label} operational summary: {len(approved)} content items published "
            f"reaching an estimated {reach:,} audience members "
            f"({engagement:.1%} engagement rate)."
        ]
        if perf > 0:
            parts.append(f"Overall performance score: {perf:.1f}/100.")
        if total_opp > 0:
            parts.append(f"Revenue opportunity identified: ${total_opp:,.0f}.")
            if priority_brand:
                parts.append(f"Priority sponsor: {priority_brand}.")
        return " ".join(parts)

    def _build_kpis(
        self,
        analytics: dict[str, Any],
        revenue: dict[str, Any],
        cost: dict[str, Any],
    ) -> list[ExecutiveKPI]:
        kpis = [
            ExecutiveKPI(
                name="Estimated Reach",
                current_value=float(analytics.get("estimated_reach", 0)),
                unit=" views",
                trend="stable",
            ),
            ExecutiveKPI(
                name="Engagement Rate",
                current_value=float(analytics.get("estimated_engagement_rate", 0)) * 100,
                unit="%",
                trend="stable",
            ),
            ExecutiveKPI(
                name="Performance Score",
                current_value=float(analytics.get("performance_score", 0)),
                unit="/100",
                trend="stable",
                target=80.0,
                on_track=float(analytics.get("performance_score", 0)) >= 80,
            ),
            ExecutiveKPI(
                name="Revenue Opportunity",
                current_value=float(revenue.get("total_opportunity_usd", 0)),
                unit=" USD",
                trend="stable",
            ),
            ExecutiveKPI(
                name="AI Cost",
                current_value=float(cost.get("session_total_usd", 0)),
                unit=" USD",
                trend="stable",
            ),
        ]
        return kpis

    def _extract_insights(
        self,
        analytics: dict[str, Any],
        revenue: dict[str, Any],
        governance: list[Any],
        lessons: list[str],
    ) -> tuple[list[str], list[str], list[str]]:
        wins: list[str] = []
        risks: list[str] = []
        opportunities: list[str] = []

        reach = analytics.get("estimated_reach", 0)
        perf = analytics.get("performance_score", 0)
        total_opp = revenue.get("total_opportunity_usd", 0)
        high_val = revenue.get("high_value_signals", 0)

        if perf >= 80:
            wins.append(f"Performance score {perf:.1f}/100 meets target threshold")
        if reach > 50_000:
            wins.append(f"Strong reach: {reach:,} estimated audience members")
        if total_opp > 10_000:
            wins.append(f"Significant revenue opportunity: ${total_opp:,.0f} identified")
        if lessons:
            wins.append(f"{len(lessons)} operational lessons captured for continuous improvement")

        if perf < 60:
            risks.append(f"Performance score {perf:.1f}/100 below minimum threshold — needs attention")
        if reach < 10_000:
            risks.append("Audience reach below 10,000 — distribution strategy needs review")
        if high_val == 0 and total_opp == 0:
            risks.append("No revenue signals detected — monetization pipeline inactive")

        if high_val > 0:
            opportunities.append(f"{high_val} high-value sponsor signal(s) ready for activation")
        if revenue.get("priority_brand"):
            opportunities.append(f"Priority brand identified: {revenue['priority_brand']}")
        for rec in analytics.get("optimisation_recommendations", [])[:3]:
            if isinstance(rec, str):
                opportunities.append(rec)

        return wins, risks, opportunities

    def _build_recommendations(
        self,
        wins: list[str],
        risks: list[str],
        opportunities: list[str],
        cost: dict[str, Any],
    ) -> list[str]:
        recs: list[str] = []
        if risks:
            recs.append(f"Address {len(risks)} identified risk(s) within 24 hours")
        if opportunities:
            recs.append("Activate identified revenue opportunities this week")
        cost_usd = float(cost.get("session_total_usd", 0))
        if cost_usd > 20:
            recs.append(f"Review AI cost optimisation — ${cost_usd:.2f} session spend detected")
        if not wins:
            recs.append("Review content strategy to improve performance metrics")
        recs.append("Continue autonomous monitoring cycles as scheduled")
        return recs

    def _extract_ai_usage(
        self, ai_metrics: dict[str, Any], cost: dict[str, Any]
    ) -> dict[str, Any]:
        total_calls = ai_metrics.get("total_calls", cost.get("total_calls", 0))
        fallback = ai_metrics.get("fallback_calls", cost.get("fallback_calls", 0))
        return {
            "total_calls": total_calls,
            "fallback_calls": fallback,
            "fallback_rate_pct": round(fallback / total_calls * 100, 1) if total_calls > 0 else 0.0,
            "validation_failures": ai_metrics.get("validation_failures", 0),
        }

    def _extract_war_room_summary(self, ws: dict[str, Any]) -> dict[str, Any]:
        return {
            "activated": ws.get("activated", False),
            "war_room_type": ws.get("war_room_type", "none"),
            "escalation_level": ws.get("escalation_level", "normal"),
        }

    def _extract_persona_summary(self, outputs: list[Any]) -> dict[str, Any]:
        return {
            "personas_activated": len(outputs),
            "persona_ids": [p.get("persona_id") for p in outputs if isinstance(p, dict)],
        }

    def _extract_governance_summary(
        self, reviews: list[Any], approved: list[Any], rejected: list[Any]
    ) -> dict[str, Any]:
        total = len(approved) + len(rejected)
        return {
            "total_reviewed": total,
            "approved": len(approved),
            "rejected": len(rejected),
            "approval_rate_pct": round(len(approved) / total * 100, 1) if total > 0 else 0.0,
        }

    def _period_start(self, period: ReportPeriod) -> datetime:
        now = datetime.utcnow()
        deltas = {
            ReportPeriod.DAILY: timedelta(days=1),
            ReportPeriod.WEEKLY: timedelta(weeks=1),
            ReportPeriod.MONTHLY: timedelta(days=30),
            ReportPeriod.QUARTERLY: timedelta(days=90),
            ReportPeriod.ANNUAL: timedelta(days=365),
            ReportPeriod.DASHBOARD: timedelta(hours=24),
        }
        return now - deltas.get(period, timedelta(days=1))

    async def _ai_insights(self, period: ReportPeriod, report: ExecutiveReport) -> str:
        try:
            import json as _json
            from sfc.ai.model_gateway import get_ai_gateway
            from sfc.ai.models import ModelRequest
            from sfc.ai.prompt_loader import get_prompt_loader

            loader = get_prompt_loader()
            system_prompt = loader.load("reporting", "executive")
            gateway = get_ai_gateway()
            request = ModelRequest(
                task_type="executive",
                system_prompt=system_prompt,
                user_message=(
                    f"Generate a concise executive insight for the {period.value} report:\n"
                    f"summary={report.executive_summary}\n"
                    f"wins={_json.dumps(report.key_wins[:3])}\n"
                    f"risks={_json.dumps(report.key_risks[:3])}\n"
                    f"revenue_opportunity_usd={report.total_revenue_opportunity_usd}\n\n"
                    'Return JSON: {"insights": str, "priority_action": str}'
                ),
                max_tokens=512,
                json_mode=True,
            )
            response = await gateway.complete(request)
            if response.success and response.parsed and not response.used_fallback:
                return response.parsed.get("insights", "")
        except Exception as exc:
            logger.debug("[ExecutiveReport] AI insights skipped: %s", exc)
        return ""
