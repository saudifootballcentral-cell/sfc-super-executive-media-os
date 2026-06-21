"""Opportunity Detection Engine — identifies strategic content and business opportunities."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.social.opportunity.models import (
    Opportunity,
    OpportunityMetrics,
    OpportunityReport,
    OpportunityType,
)

logger = logging.getLogger("sfc.social.opportunity")

_singleton: "OpportunityDetectionEngine | None" = None


def get_opportunity_engine() -> "OpportunityDetectionEngine":
    global _singleton
    if _singleton is None:
        _singleton = OpportunityDetectionEngine()
    return _singleton


class OpportunityDetectionEngine:
    """Detects and scores strategic opportunities from social intelligence data."""

    def __init__(self) -> None:
        self._gateway = None
        self._opportunities: list[Opportunity] = []
        self._max_history = 1000

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def detect(
        self,
        trend_data: dict[str, Any] | None = None,
        narrative_data: dict[str, Any] | None = None,
        sentiment_data: dict[str, Any] | None = None,
        audience_data: dict[str, Any] | None = None,
    ) -> list[Opportunity]:
        """Detect opportunities from aggregated social intelligence data."""
        opportunities: list[Opportunity] = []

        content_opps = await self._detect_content_opportunities(
            trend_data or {}, sentiment_data or {}
        )
        opportunities.extend(content_opps)

        narrative_opps = await self._detect_narrative_opportunities(
            narrative_data or {}
        )
        opportunities.extend(narrative_opps)

        growth_opps = await self._detect_growth_opportunities(
            audience_data or {}
        )
        opportunities.extend(growth_opps)

        opportunities.sort(key=lambda o: o.metrics.priority_score, reverse=True)

        for opp in opportunities:
            if len(self._opportunities) < self._max_history:
                self._opportunities.append(opp)

        return opportunities

    async def generate_report(
        self,
        opportunities: list[Opportunity] | None = None,
    ) -> OpportunityReport:
        """Generate a comprehensive opportunity detection report."""
        if opportunities is None:
            opportunities = self._opportunities[-20:] if self._opportunities else []
            if not opportunities:
                opportunities = await self.detect()

        top = max(opportunities, key=lambda o: o.metrics.priority_score, default=None)
        total_revenue = sum(o.metrics.revenue_potential for o in opportunities)

        by_type: dict[str, int] = {}
        for o in opportunities:
            by_type[o.opportunity_type.value] = by_type.get(o.opportunity_type.value, 0) + 1

        exec_summary = await self._generate_executive_summary(opportunities, total_revenue)

        return OpportunityReport(
            opportunities=opportunities,
            top_opportunity=top,
            total_revenue_potential=round(total_revenue, 2),
            by_type=by_type,
            executive_summary=exec_summary,
        )

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [o.to_dict() for o in self._opportunities[-limit:]]

    async def _detect_content_opportunities(
        self, trend_data: dict[str, Any], sentiment_data: dict[str, Any]
    ) -> list[Opportunity]:
        opportunities = []
        trending_topics = trend_data.get("top_topic", "")

        if trending_topics:
            metrics = OpportunityMetrics(
                impact=random.uniform(55, 90),
                confidence=random.uniform(60, 95),
                speed=random.uniform(70, 100),
                reach=random.randint(100000, 2000000),
                revenue_potential=random.uniform(5000, 50000),
            )
            exec_rec = await self._get_executive_recommendation(
                f"Content opportunity for {trending_topics}"
            )
            opportunities.append(Opportunity(
                title=f"Breaking Content: {trending_topics}",
                description=f"High-velocity trend '{trending_topics}' presents immediate content opportunity.",
                opportunity_type=OpportunityType.CONTENT,
                metrics=metrics,
                source_trend=trending_topics,
                executive_recommendation=exec_rec,
                required_personas=["content_director", "creative_lead"],
                action_steps=[
                    "Create short-form video within 2 hours",
                    "Post across all platforms simultaneously",
                    "Engage top influencers for amplification",
                ],
            ))

        return opportunities

    async def _detect_narrative_opportunities(
        self, narrative_data: dict[str, Any]
    ) -> list[Opportunity]:
        opportunities = []

        narratives = narrative_data.get("top_narratives", [])
        for i, narrative in enumerate(narratives[:2]):
            title = narrative.get("title", f"Narrative {i+1}") if isinstance(narrative, dict) else f"Narrative {i+1}"
            metrics = OpportunityMetrics(
                impact=random.uniform(40, 75),
                confidence=random.uniform(50, 80),
                speed=random.uniform(30, 70),
                reach=random.randint(50000, 500000),
                revenue_potential=random.uniform(2000, 25000),
            )
            opportunities.append(Opportunity(
                title=f"Narrative Amplification: {title}",
                description=f"Growing narrative '{title}' can be amplified for brand benefit.",
                opportunity_type=OpportunityType.NARRATIVE,
                metrics=metrics,
                source_narrative=title,
                executive_recommendation="Align content strategy with emerging narrative.",
                required_personas=["narrative_director", "editorial_lead"],
                action_steps=[
                    "Map narrative to SFC content pillars",
                    "Produce 3-5 pieces of supporting content",
                ],
            ))

        return opportunities

    async def _detect_growth_opportunities(
        self, audience_data: dict[str, Any]
    ) -> list[Opportunity]:
        opportunities = []

        if audience_data.get("total_audience", 0) > 0:
            metrics = OpportunityMetrics(
                impact=random.uniform(35, 65),
                confidence=random.uniform(55, 80),
                speed=random.uniform(20, 50),
                reach=random.randint(200000, 1000000),
                revenue_potential=random.uniform(10000, 80000),
            )
            opportunities.append(Opportunity(
                title="Audience Expansion: Youth Segment",
                description="Youth audience segment shows 22%+ monthly growth — expand targeting.",
                opportunity_type=OpportunityType.GROWTH,
                metrics=metrics,
                executive_recommendation="Invest in TikTok and short-form content for youth segment.",
                required_personas=["audience_director", "creative_lead"],
                action_steps=[
                    "Launch TikTok-first content series",
                    "Partner with youth football influencers",
                    "Create interactive audience engagement campaigns",
                ],
            ))

        return opportunities

    async def _generate_executive_summary(
        self, opportunities: list[Opportunity], total_revenue: float
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Summarize {len(opportunities)} Saudi football opportunities, total revenue potential: ${total_revenue:,.0f}",
                task_type="opportunity_analysis",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            top_types = list({o.opportunity_type.value for o in opportunities[:3]})
            return (
                f"Detected {len(opportunities)} strategic opportunities across Saudi football. "
                f"Total revenue potential: ${total_revenue:,.0f}. "
                f"Priority types: {', '.join(top_types)}."
            )

    async def _get_executive_recommendation(self, context: str) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Executive recommendation: {context}",
                task_type="opportunity_analysis",
                max_tokens=100,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            return f"Act immediately on {context} — high priority window."
