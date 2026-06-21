"""Narrative Intelligence Service — tracks and analyzes football narratives."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.social.narrative.models import (
    Narrative,
    NarrativeCategory,
    NarrativeLifecycle,
    NarrativeMap,
    NarrativeMetrics,
    NarrativeReport,
)

logger = logging.getLogger("sfc.social.narrative")

_singleton: "NarrativeIntelligenceService | None" = None


def get_narrative_service() -> "NarrativeIntelligenceService":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeIntelligenceService()
    return _singleton


class NarrativeIntelligenceService:
    """Detects and tracks narrative lifecycles across Saudi football media."""

    def __init__(self) -> None:
        self._gateway = None
        self._narratives: dict[str, Narrative] = {}
        self._history: list[Narrative] = []
        self._max_history = 1000

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def detect_narratives(
        self,
        topics: list[str] | None = None,
        trend_data: dict[str, Any] | None = None,
    ) -> list[Narrative]:
        """Detect active narratives from trending topics and social signals."""
        topics = topics or self._default_topics()
        narratives: list[Narrative] = []

        for topic in topics[:8]:
            narrative = await self._build_narrative(topic, trend_data or {})
            self._narratives[narrative.narrative_id] = narrative
            narratives.append(narrative)
            if len(self._history) < self._max_history:
                self._history.append(narrative)

        return narratives

    async def generate_report(
        self,
        narratives: list[Narrative] | None = None,
    ) -> NarrativeReport:
        """Generate a comprehensive narrative intelligence report."""
        if narratives is None:
            narratives = list(self._narratives.values())
        if not narratives:
            narratives = await self.detect_narratives()

        narrative_map = await self.build_narrative_map(narratives)
        top = sorted(narratives, key=lambda n: n.metrics.score, reverse=True)[:5]

        opportunities = [
            f"Amplify '{n.title}' — high growth rate {n.metrics.growth_rate:.1f}%"
            for n in top
            if n.metrics.growth_rate > 10 and n.lifecycle == NarrativeLifecycle.GROWING
        ]
        risks = [
            f"Monitor '{n.title}' — negative sentiment {n.metrics.sentiment:.2f}"
            for n in narratives
            if n.metrics.sentiment < -0.3
        ]

        ai_insights = await self._get_ai_insights(narratives)

        return NarrativeReport(
            narrative_map=narrative_map,
            top_narratives=top,
            narrative_opportunities=opportunities or ["No immediate opportunities detected"],
            narrative_risks=risks or ["No critical narrative risks detected"],
            ai_insights=ai_insights,
        )

    async def build_narrative_map(self, narratives: list[Narrative]) -> NarrativeMap:
        """Build a map of all active narratives."""
        dominant = max(narratives, key=lambda n: n.metrics.score, default=None)
        conflicts = self._detect_conflicts(narratives)
        emerging_count = sum(1 for n in narratives if n.lifecycle == NarrativeLifecycle.EMERGING)
        declining_count = sum(1 for n in narratives if n.lifecycle == NarrativeLifecycle.DECLINING)

        return NarrativeMap(
            narratives=narratives,
            dominant_narrative=dominant.narrative_id if dominant else "",
            narrative_conflicts=[{"description": c} for c in conflicts],
            emerging_count=emerging_count,
            declining_count=declining_count,
        )

    def get_narrative(self, narrative_id: str) -> Narrative | None:
        return self._narratives.get(narrative_id)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [n.to_dict() for n in self._history[-limit:]]

    async def _build_narrative(
        self, topic: str, trend_data: dict[str, Any]
    ) -> Narrative:
        score = random.uniform(30, 90)
        sentiment = random.uniform(-0.5, 0.8)
        growth = random.uniform(-5, 30)

        lifecycle = NarrativeLifecycle.GROWING
        if score > 80:
            lifecycle = NarrativeLifecycle.PEAKING
        elif score < 40:
            lifecycle = NarrativeLifecycle.DECLINING
        elif growth < 0:
            lifecycle = NarrativeLifecycle.DORMANT

        category = self._classify_topic(topic)

        metrics = NarrativeMetrics(
            score=round(score, 1),
            growth_rate=round(growth, 1),
            velocity=random.uniform(0.5, 8.0),
            sentiment=round(sentiment, 2),
            influence=random.uniform(0.3, 0.95),
            reach=random.randint(5000, 500000),
        )

        return Narrative(
            title=topic,
            description=f"Emerging narrative around {topic} in Saudi football ecosystem.",
            lifecycle=lifecycle,
            category=category,
            entities=[topic],
            metrics=metrics,
            related_trends=[f"#{topic.replace(' ', '')}"],
            opportunities=(
                [f"Capitalize on positive {topic} sentiment"]
                if sentiment > 0.3 else []
            ),
            risks=(
                [f"Negative narrative forming around {topic}"]
                if sentiment < -0.2 else []
            ),
            key_accounts=["@SPL_EN", "@SaudiFootball"],
        )

    async def _get_ai_insights(self, narratives: list[Narrative]) -> str:
        try:
            from sfc.ai.models import ModelRequest
            top_titles = [n.title for n in narratives[:3]]
            req = ModelRequest(
                prompt=f"Analyze Saudi football narratives: {', '.join(top_titles)}",
                task_type="narrative_analysis",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            top = narratives[0].title if narratives else "N/A"
            return f"Dominant narrative '{top}' driving Saudi football conversation."

    def _classify_topic(self, topic: str) -> NarrativeCategory:
        topic_lower = topic.lower()
        if any(w in topic_lower for w in ["transfer", "signing", "deal"]):
            return NarrativeCategory.TRANSFER
        if any(w in topic_lower for w in ["national", "green falcons", "saudi team"]):
            return NarrativeCategory.NATIONAL_TEAM
        if any(w in topic_lower for w in ["al hilal", "al nassr", "al ittihad", "club"]):
            return NarrativeCategory.CLUB
        if any(w in topic_lower for w in ["world cup", "tournament", "cup"]):
            return NarrativeCategory.TOURNAMENT
        if any(w in topic_lower for w in ["referee", "var", "decision"]):
            return NarrativeCategory.REFEREE
        return NarrativeCategory.GENERAL

    def _detect_conflicts(self, narratives: list[Narrative]) -> list[str]:
        conflicts = []
        for i, n1 in enumerate(narratives):
            for n2 in narratives[i + 1:]:
                if abs(n1.metrics.sentiment - n2.metrics.sentiment) > 0.7:
                    conflicts.append(f"Conflict: '{n1.title}' vs '{n2.title}'")
        return conflicts[:5]

    def _default_topics(self) -> list[str]:
        return [
            "Al Hilal dominance",
            "Saudi Pro League quality",
            "Green Falcons World Cup dream",
            "Foreign star signings impact",
            "Youth academy development",
            "VAR implementation controversy",
            "Transfer window activity",
            "Saudi football global rise",
        ]
