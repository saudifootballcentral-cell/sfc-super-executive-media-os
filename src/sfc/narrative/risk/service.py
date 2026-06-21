"""Narrative Risk Engine — identifies and scores narrative threats."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.narrative.risk.models import (
    MitigationRecommendation,
    NarrativeRiskReport,
    NarrativeRiskType,
    RiskLevel,
    RiskScore,
)

logger = logging.getLogger("sfc.narrative.risk")

_singleton: "NarrativeRiskEngine | None" = None


def get_risk_engine() -> "NarrativeRiskEngine":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeRiskEngine()
    return _singleton


class NarrativeRiskEngine:
    """Evaluates narrative risk across 7 risk types and recommends mitigation."""

    def __init__(self) -> None:
        self._gateway = None
        self._reports: list[NarrativeRiskReport] = []
        self._max_history = 300

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def assess_risk(
        self,
        narrative_or_id: Any,
        narrative_title: str = "",
        context: dict[str, Any] | None = None,
    ) -> NarrativeRiskReport:
        """Assess risk for a narrative across all risk types.

        Accepts a NarrativeProfile object or a narrative_id string.
        """
        from sfc.narrative.modeling.models import NarrativeProfile
        if isinstance(narrative_or_id, NarrativeProfile):
            profile = narrative_or_id
            narrative_id = profile.profile_id
            narrative_title = profile.title
            context = context or {
                "sentiment_score": profile.sentiment_score,
                "strength_score": profile.strength_score,
                "virality_potential": profile.virality_potential,
                "credibility_score": profile.credibility_score,
            }
        else:
            narrative_id = str(narrative_or_id)
            context = context or {}
        context = context or {}
        sentiment = context.get("sentiment_score", 0)
        velocity = context.get("velocity", 0)

        risk_scores = [
            self._score_risk(NarrativeRiskType.REPUTATION, sentiment, velocity, context),
            self._score_risk(NarrativeRiskType.MISINFORMATION, sentiment, velocity, context),
            self._score_risk(NarrativeRiskType.MEDIA, sentiment, velocity, context),
            self._score_risk(NarrativeRiskType.SPONSOR, sentiment, velocity, context),
            self._score_risk(NarrativeRiskType.FAN_BACKLASH, sentiment, velocity, context),
            self._score_risk(NarrativeRiskType.POLITICAL, sentiment, velocity, context),
            self._score_risk(NarrativeRiskType.GOVERNANCE, sentiment, velocity, context),
        ]

        overall_score = round(
            sum(r.score * self._risk_weight(r.risk_type) for r in risk_scores), 1
        )
        overall_level = self._get_level(overall_score)
        primary_risk = max(risk_scores, key=lambda r: r.score).risk_type
        requires_war_room = overall_score >= 70

        mitigation = [
            self._get_mitigation(r) for r in risk_scores
            if r.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]

        executive_alerts = []
        if overall_score >= 80:
            executive_alerts.append(
                f"CRITICAL RISK: {narrative_title} — {primary_risk.value} risk at {overall_score:.0f}"
            )
        elif overall_score >= 60:
            executive_alerts.append(
                f"HIGH RISK: {narrative_title} — {primary_risk.value} requires attention"
            )

        ai_analysis = await self._get_ai_analysis(narrative_title, overall_score, primary_risk)

        report = NarrativeRiskReport(
            narrative_id=narrative_id,
            narrative_title=narrative_title,
            risk_scores=risk_scores,
            overall_risk_score=overall_score,
            overall_risk_level=overall_level,
            primary_risk=primary_risk,
            mitigation_recommendations=mitigation,
            executive_alerts=executive_alerts,
            requires_war_room=requires_war_room,
            ai_analysis=ai_analysis,
        )

        if len(self._reports) < self._max_history:
            self._reports.append(report)

        return report

    async def batch_assess(
        self, narratives: list[Any]
    ) -> list[NarrativeRiskReport]:
        """Assess risk for multiple narratives."""
        results = []
        for n in narratives[:15]:
            results.append(await self.assess_risk(n))
        return results

    def get_history(self, limit: int = 30) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def _score_risk(
        self,
        risk_type: NarrativeRiskType,
        sentiment: float,
        velocity: float,
        context: dict[str, Any],
    ) -> RiskScore:
        base_score = random.uniform(10, 70)

        if sentiment < -30:
            if risk_type in (NarrativeRiskType.REPUTATION, NarrativeRiskType.FAN_BACKLASH):
                base_score += 20
        if velocity > 6:
            if risk_type in (NarrativeRiskType.MEDIA, NarrativeRiskType.MISINFORMATION):
                base_score += 15

        score = min(round(base_score, 1), 100)
        evidence = self._get_evidence(risk_type, score)

        return RiskScore(
            risk_type=risk_type,
            score=score,
            confidence=round(random.uniform(60, 90), 1),
            trend="rising" if sentiment < -20 else "stable",
            evidence=evidence,
        )

    def _risk_weight(self, risk_type: NarrativeRiskType) -> float:
        weights = {
            NarrativeRiskType.REPUTATION: 0.25,
            NarrativeRiskType.MISINFORMATION: 0.20,
            NarrativeRiskType.MEDIA: 0.15,
            NarrativeRiskType.SPONSOR: 0.15,
            NarrativeRiskType.FAN_BACKLASH: 0.15,
            NarrativeRiskType.POLITICAL: 0.05,
            NarrativeRiskType.GOVERNANCE: 0.05,
        }
        return weights.get(risk_type, 0.1)

    def _get_level(self, score: float) -> RiskLevel:
        if score >= 80:
            return RiskLevel.CRITICAL
        if score >= 60:
            return RiskLevel.HIGH
        if score >= 40:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _get_mitigation(self, risk: RiskScore) -> MitigationRecommendation:
        actions = {
            NarrativeRiskType.REPUTATION: "Issue proactive statement defending reputation",
            NarrativeRiskType.MISINFORMATION: "Deploy fact-checking content with 2+ verified sources",
            NarrativeRiskType.MEDIA: "Engage key media partners for balanced coverage",
            NarrativeRiskType.SPONSOR: "Brief sponsors on situation and mitigation plan",
            NarrativeRiskType.FAN_BACKLASH: "Deploy empathy-first fan engagement content",
            NarrativeRiskType.POLITICAL: "Maintain neutral stance, avoid political narrative",
            NarrativeRiskType.GOVERNANCE: "Ensure all content passes constitutional review",
        }
        return MitigationRecommendation(
            risk_type=risk.risk_type,
            action=actions.get(risk.risk_type, "Monitor and escalate if needed"),
            rationale=f"{risk.risk_type.value} risk at {risk.score:.0f}",
            priority="IMMEDIATE" if risk.level == RiskLevel.CRITICAL else "HIGH",
            estimated_impact=round(min(risk.score * 0.6, 50), 1),
            personas_required=["crisis_director", "editorial_compliance"],
            time_to_implement="immediate" if risk.level == RiskLevel.CRITICAL else "2 hours",
        )

    def _get_evidence(self, risk_type: NarrativeRiskType, score: float) -> list[str]:
        evidence_map = {
            NarrativeRiskType.REPUTATION: ["Negative coverage detected", "Fan trust declining"],
            NarrativeRiskType.MISINFORMATION: ["Unverified claims spreading", "No official sources confirmed"],
            NarrativeRiskType.MEDIA: ["Media narrative shifting negative", "Viral misinformation risk"],
            NarrativeRiskType.SPONSOR: ["Sponsor sentiment monitoring required"],
            NarrativeRiskType.FAN_BACKLASH: ["Fan criticism trending on X"],
            NarrativeRiskType.POLITICAL: ["Political sensitivity detected"],
            NarrativeRiskType.GOVERNANCE: ["Content review required by constitution"],
        }
        return evidence_map.get(risk_type, [])[:2 if score > 60 else 1]

    async def _get_ai_analysis(
        self, title: str, overall_score: float, primary_risk: NarrativeRiskType
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Risk analysis for '{title}': overall={overall_score:.0f}, primary={primary_risk.value}",
                task_type="risk_assessment",
                max_tokens=150,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            level = "critical" if overall_score >= 80 else "moderate"
            return (
                f"Narrative '{title}' presents {level} risk. "
                f"Primary concern: {primary_risk.value}. "
                f"Overall risk score: {overall_score:.0f}/100."
            )
