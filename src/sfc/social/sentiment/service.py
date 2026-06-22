"""Fan Sentiment Service — measures fan emotion across Saudi football."""

from __future__ import annotations

import logging
from typing import Any

from sfc.social.sentiment.models import (
    FanPulseReport,
    SentimentCategory,
    SentimentMetrics,
    SentimentTarget,
    SentimentTarget_,
)

logger = logging.getLogger("sfc.social.sentiment")

_singleton: "FanSentimentService | None" = None

_ENTITY_DISPLAY_NAMES: dict[str, str] = {
    "al_hilal_club": "Al Hilal",
    "al_nassr_club": "Al Nassr",
    "al_ittihad_club": "Al Ittihad",
    "green_falcons_national_team": "Green Falcons",
    "cristiano_ronaldo": "Cristiano Ronaldo",
    "neymar_player": "Neymar",
    "saudi_pro_league": "SPL",
    "coach_roberto_mancini": "National team coach",
}

_FIXTURE_ENTITY_MAP: dict[str, str] = {
    "al_hilal_club": "Al Hilal",
    "al_nassr_club": "Al Nassr",
    "al_ittihad_club": "Al Ittihad",
    "green_falcons_national_team": "Green Falcons",
    "cristiano_ronaldo": "Cristiano Ronaldo",
    "neymar_player": "Neymar",
    "saudi_pro_league": "SPL",
    "coach_roberto_mancini": "Saudi Football Federation",
}


def get_sentiment_service() -> "FanSentimentService":
    global _singleton
    if _singleton is None:
        _singleton = FanSentimentService()
    return _singleton


class FanSentimentService:
    """Measures and tracks fan sentiment across Saudi football entities."""

    def __init__(self) -> None:
        self._gateway = None
        self._targets: dict[str, SentimentTarget_] = {}
        self._history: list[FanPulseReport] = []
        self._max_history = 500

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def analyze(
        self,
        entity_ids: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[SentimentTarget_]:
        """Analyze sentiment for given entities (or defaults)."""
        entities = entity_ids or self._default_entities()
        results: list[SentimentTarget_] = []

        for entity_id in entities[:12]:
            target = await self._analyze_entity(entity_id, context or {})
            self._targets[entity_id] = target
            results.append(target)

        return results

    async def generate_fan_pulse_report(
        self,
        targets: list[SentimentTarget_] | None = None,
    ) -> FanPulseReport:
        """Generate a comprehensive fan pulse report."""
        if targets is None:
            targets = await self.analyze()

        overall_score = (
            sum(t.metrics.score for t in targets) / len(targets) if targets else 0.0
        )

        overall_category: SentimentCategory
        if overall_score > 20:
            overall_category = SentimentCategory.POSITIVE
        elif overall_score < -20:
            overall_category = SentimentCategory.NEGATIVE
        else:
            overall_category = SentimentCategory.NEUTRAL

        alerts = [
            f"SENTIMENT CRISIS: {t.entity_name} at {t.metrics.score:.0f}"
            for t in targets
            if t.metrics.score < -50
        ]
        opportunities = [
            f"Amplify positive sentiment for {t.entity_name} ({t.metrics.score:.0f})"
            for t in targets
            if t.metrics.score > 60 and t.metrics.momentum > 5
        ]

        ai_insights = await self._get_ai_insights(targets, overall_score)

        report = FanPulseReport(
            tracked_entities=targets,
            overall_score=round(overall_score, 1),
            overall_category=overall_category,
            alerts=alerts,
            opportunities=opportunities,
            ai_insights=ai_insights,
        )

        if len(self._history) < self._max_history:
            self._history.append(report)

        return report

    async def get_alerts(self) -> list[str]:
        """Return current sentiment crisis alerts."""
        alerts = []
        for target in self._targets.values():
            if target.metrics.score < -50:
                alerts.append(
                    f"CRISIS: {target.entity_name} sentiment at {target.metrics.score:.0f}"
                )
            elif target.metrics.score < -30 and target.metrics.momentum < -10:
                alerts.append(
                    f"WARNING: {target.entity_name} sentiment declining rapidly"
                )
        return alerts

    def get_target(self, entity_id: str) -> SentimentTarget_ | None:
        return self._targets.get(entity_id)

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    async def _analyze_entity(
        self, entity_id: str, context: dict[str, Any]
    ) -> SentimentTarget_:
        from sfc.data.fixtures.loader import get_fixture_loader
        loader = get_fixture_loader()
        fixture_key = _FIXTURE_ENTITY_MAP.get(entity_id, entity_id.replace("_", " ").title())
        data = loader.get_sentiment(fixture_key)

        score: float = float(data.get("sentiment_score", 55.0))
        momentum: float = float(data.get("momentum", 0.5))
        volatility: float = float(data.get("volatility", 10.0))
        confidence: float = float(data.get("confidence", 75.0))
        sample_size: int = int(data.get("sample_size", 5000))

        target_type = self._infer_target_type(entity_id)
        metrics = SentimentMetrics(
            score=round(score, 1),
            momentum=round(momentum, 1),
            volatility=round(volatility, 1),
            confidence=round(confidence, 1),
            sample_size=sample_size,
        )

        return SentimentTarget_(
            entity_id=entity_id,
            entity_name=_ENTITY_DISPLAY_NAMES.get(entity_id, entity_id.replace("_", " ").title()),
            target_type=target_type,
            metrics=metrics,
            recent_drivers=self._get_drivers(entity_id, score),
        )

    async def _get_ai_insights(
        self, targets: list[SentimentTarget_], overall_score: float
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Saudi football fan sentiment — overall: {overall_score:.0f}. Top entities: {[t.entity_name for t in targets[:3]]}",
                task_type="sentiment_analysis",
                max_tokens=150,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            category = "positive" if overall_score > 0 else "negative"
            return f"Overall fan sentiment is {category} (score: {overall_score:.0f})."

    def _infer_target_type(self, entity_id: str) -> SentimentTarget:
        eid = entity_id.lower()
        if any(w in eid for w in ["player", "ronaldo", "neymar", "salah"]):
            return SentimentTarget.PLAYER
        if any(w in eid for w in ["coach", "manager", "trainer"]):
            return SentimentTarget.COACH
        if any(w in eid for w in ["club", "hilal", "nassr", "ittihad"]):
            return SentimentTarget.CLUB
        if any(w in eid for w in ["national", "green_falcons", "saudi_team"]):
            return SentimentTarget.NATIONAL_TEAM
        if any(w in eid for w in ["league", "cup", "tournament"]):
            return SentimentTarget.COMPETITION
        return SentimentTarget.CLUB

    def _get_drivers(self, entity_id: str, score: float) -> list[str]:
        if score > 50:
            return [f"Recent strong performance by {entity_id}", "Positive media coverage"]
        if score < -20:
            return [f"Controversy surrounding {entity_id}", "Fan criticism online"]
        return [f"Mixed reactions to {entity_id} news"]

    def _default_entities(self) -> list[str]:
        return [
            "al_hilal_club",
            "al_nassr_club",
            "al_ittihad_club",
            "green_falcons_national_team",
            "cristiano_ronaldo",
            "neymar_player",
            "saudi_pro_league",
            "coach_roberto_mancini",
        ]
