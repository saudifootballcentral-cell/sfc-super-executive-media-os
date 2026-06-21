"""Narrative Strategy Engine — recommends strategic actions for narratives."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.narrative.strategy.models import (
    NarrativeStrategyReport,
    StrategyAction,
    StrategyPriority,
    StrategyRecommendation,
)

logger = logging.getLogger("sfc.narrative.strategy")

_singleton: "NarrativeStrategyEngine | None" = None


def get_strategy_engine() -> "NarrativeStrategyEngine":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeStrategyEngine()
    return _singleton


class NarrativeStrategyEngine:
    """Recommends strategic narrative actions based on lifecycle, risk, and opportunity signals."""

    def __init__(self) -> None:
        self._gateway = None
        self._reports: list[NarrativeStrategyReport] = []
        self._max_history = 300

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def recommend(
        self,
        narratives: Any,
        risk_context: Any | None = None,
        risk_report: Any | None = None,
        forecast_context: dict[str, Any] | None = None,
    ) -> NarrativeStrategyReport:
        """Generate strategy recommendations for narrative(s).

        Accepts a single NarrativeProfile, a list of NarrativeProfiles, or a list of dicts.
        """
        from sfc.narrative.modeling.models import NarrativeProfile
        from sfc.narrative.risk.models import NarrativeRiskReport

        if isinstance(narratives, NarrativeProfile):
            narrative_list = [narratives.model_dump(mode="json")]
        elif isinstance(narratives, list):
            narrative_list = [
                n.model_dump(mode="json") if isinstance(n, NarrativeProfile) else n
                for n in narratives
            ]
        else:
            narrative_list = [{"title": str(narratives)}]

        risk_ctx: dict[str, Any] = {}
        if isinstance(risk_context, dict):
            risk_ctx = risk_context
        elif isinstance(risk_report, NarrativeRiskReport):
            risk_ctx = {"overall_risk_score": risk_report.overall_risk_score}

        forecast_ctx = forecast_context or {}

        recommendations: list[StrategyRecommendation] = []
        for narrative in narrative_list[:10]:
            rec = await self._recommend_for_narrative(narrative, risk_ctx, forecast_ctx)
            recommendations.append(rec)

        recommendations.sort(key=lambda r: r.impact_score, reverse=True)
        top = recommendations[0] if recommendations else None
        immediate = [r for r in recommendations if r.priority == StrategyPriority.IMMEDIATE]

        by_action: dict[str, int] = {}
        for r in recommendations:
            by_action[r.action.value] = by_action.get(r.action.value, 0) + 1

        war_room_escalations = [
            f"War room required for: {r.narrative_title}"
            for r in recommendations
            if r.war_room_required
        ]

        exec_summary = await self._get_executive_summary(recommendations)

        report = NarrativeStrategyReport(
            recommendations=recommendations,
            top_recommendation=top,
            immediate_actions=immediate,
            by_action_type=by_action,
            executive_summary=exec_summary,
            war_room_escalations=war_room_escalations,
        )

        if len(self._reports) < self._max_history:
            self._reports.append(report)

        return report

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    async def _recommend_for_narrative(
        self,
        narrative: dict[str, Any],
        risk_ctx: dict[str, Any],
        forecast_ctx: dict[str, Any],
    ) -> StrategyRecommendation:
        title = narrative.get("title", "")
        narrative_id = narrative.get("profile_id", narrative.get("narrative_id", ""))
        strength = narrative.get("strength_score", 50.0)
        sentiment = narrative.get("sentiment_score", 0.0)
        virality = narrative.get("virality_potential", 50.0)
        risk_score = risk_ctx.get("overall_risk_score", 30.0)

        action = self._determine_action(strength, sentiment, virality, risk_score)
        priority = self._determine_priority(action, risk_score, virality)

        action_steps = await self._get_action_steps(title, action)
        expected_outcome = self._get_expected_outcome(action, strength, sentiment)

        return StrategyRecommendation(
            narrative_id=narrative_id,
            narrative_title=title,
            action=action,
            priority=priority,
            rationale=self._get_rationale(action, strength, sentiment, virality),
            expected_outcome=expected_outcome,
            confidence=round(random.uniform(60, 90), 1),
            effort_score=self._get_effort_score(action),
            impact_score=round(strength * 0.5 + virality * 0.5, 1),
            personas_required=self._get_personas(action),
            action_steps=action_steps,
            success_metrics=self._get_success_metrics(action),
            war_room_required=risk_score >= 70,
            expires_in_hours=24.0 if priority == StrategyPriority.IMMEDIATE else None,
        )

    def _determine_action(
        self, strength: float, sentiment: float, virality: float, risk_score: float
    ) -> StrategyAction:
        # sentiment is 0-100; below 30 is negative territory
        if sentiment < 30 and strength > 70:
            return StrategyAction.COUNTER
        if risk_score >= 70 and sentiment < 40:
            return StrategyAction.REDIRECT
        if strength > 70 and sentiment > 60 and virality > 60:
            return StrategyAction.AMPLIFY
        if strength > 50 and sentiment > 50:
            return StrategyAction.SUPPORT
        if risk_score >= 50 and sentiment < 50:
            return StrategyAction.MONITOR
        if strength > 30 and virality > 40:
            return StrategyAction.ACCELERATE
        return StrategyAction.SUPPORT

    def _determine_priority(
        self, action: StrategyAction, risk_score: float, virality: float
    ) -> StrategyPriority:
        if action == StrategyAction.COUNTER and risk_score >= 70:
            return StrategyPriority.IMMEDIATE
        if action == StrategyAction.AMPLIFY and virality > 70:
            return StrategyPriority.HIGH
        if action in (StrategyAction.REDIRECT, StrategyAction.ACCELERATE):
            return StrategyPriority.HIGH
        if action == StrategyAction.MONITOR:
            return StrategyPriority.LOW
        return StrategyPriority.MEDIUM

    async def _get_action_steps(self, title: str, action: StrategyAction) -> list[str]:
        step_templates = {
            StrategyAction.AMPLIFY: [
                f"Create 3-5 pieces of content supporting '{title}'",
                "Engage top influencers for organic amplification",
                "Schedule content across all platforms at peak hours",
            ],
            StrategyAction.COUNTER: [
                "Prepare factual rebuttal with 2+ verified sources",
                "Brief crisis team on narrative situation",
                "Deploy counter-narrative through trusted channels",
            ],
            StrategyAction.REDIRECT: [
                "Identify alternative narrative to pivot audience attention",
                "Create high-engagement content on alternative topic",
                "Gradually reduce coverage of original narrative",
            ],
            StrategyAction.SUPPORT: [
                f"Align content strategy with '{title}' narrative",
                "Produce supporting content across 2-3 platforms",
                "Monitor sentiment and adjust messaging",
            ],
            StrategyAction.ACCELERATE: [
                "Inject narrative into trending conversations",
                "Coordinate influencer posts within 2-hour window",
                "Deploy paid amplification for rapid reach",
            ],
            StrategyAction.MONITOR: [
                "Set up 24/7 monitoring alerts for narrative changes",
                "Review sentiment metrics every 6 hours",
                "Prepare response template for rapid deployment",
            ],
        }
        return step_templates.get(action, ["Monitor and evaluate situation"])

    def _get_rationale(
        self, action: StrategyAction, strength: float, sentiment: float, virality: float
    ) -> str:
        rationales = {
            StrategyAction.AMPLIFY: f"High virality ({virality:.0f}) and positive sentiment ({sentiment:.0f}) — ideal amplification window",
            StrategyAction.COUNTER: f"Negative sentiment ({sentiment:.0f}) and high risk require immediate counter-narrative",
            StrategyAction.REDIRECT: f"Risk indicators suggest redirecting audience attention is safer",
            StrategyAction.SUPPORT: f"Moderate strength ({strength:.0f}) — supportive content will strengthen narrative",
            StrategyAction.ACCELERATE: f"Growth signals detected — acceleration will maximize reach before peak",
            StrategyAction.MONITOR: f"Low risk and strength — monitoring sufficient at this stage",
            StrategyAction.DELAY: "Timing is suboptimal — delay for better moment",
            StrategyAction.IGNORE: "Narrative too weak to warrant resource investment",
        }
        return rationales.get(action, "Strategic action recommended based on current signals")

    def _get_expected_outcome(
        self, action: StrategyAction, strength: float, sentiment: float
    ) -> str:
        outcomes = {
            StrategyAction.AMPLIFY: f"Expected 2-3x reach increase within 24 hours",
            StrategyAction.COUNTER: "Expected 30-50% reduction in negative narrative velocity",
            StrategyAction.REDIRECT: "Audience attention shifted to positive narrative within 48 hours",
            StrategyAction.SUPPORT: "Narrative strength reinforced, sentiment maintained",
            StrategyAction.ACCELERATE: "Narrative reaches mainstream 12-18 hours earlier than organic",
            StrategyAction.MONITOR: "Early warning system active for escalation detection",
        }
        return outcomes.get(action, "Positive narrative outcome expected")

    def _get_effort_score(self, action: StrategyAction) -> float:
        effort = {
            StrategyAction.AMPLIFY: 60.0,
            StrategyAction.COUNTER: 80.0,
            StrategyAction.REDIRECT: 75.0,
            StrategyAction.SUPPORT: 40.0,
            StrategyAction.ACCELERATE: 65.0,
            StrategyAction.MONITOR: 20.0,
            StrategyAction.DELAY: 10.0,
            StrategyAction.IGNORE: 5.0,
        }
        return effort.get(action, 50.0)

    def _get_personas(self, action: StrategyAction) -> list[str]:
        persona_map = {
            StrategyAction.AMPLIFY: ["content_director", "creative_lead", "social_commander"],
            StrategyAction.COUNTER: ["crisis_director", "editorial_compliance", "narrative_specialist"],
            StrategyAction.REDIRECT: ["narrative_specialist", "content_director"],
            StrategyAction.SUPPORT: ["content_director", "social_commander"],
            StrategyAction.ACCELERATE: ["social_commander", "creative_lead"],
            StrategyAction.MONITOR: ["sentiment_analyst"],
        }
        return persona_map.get(action, ["content_director"])

    def _get_success_metrics(self, action: StrategyAction) -> list[str]:
        metrics = {
            StrategyAction.AMPLIFY: ["Reach target: 2x baseline", "Engagement rate: >5%"],
            StrategyAction.COUNTER: ["Negative sentiment down 30%", "Narrative velocity reduced"],
            StrategyAction.REDIRECT: ["New narrative reach: 3x original", "Original narrative declining"],
            StrategyAction.SUPPORT: ["Narrative strength maintained >60", "Sentiment positive"],
            StrategyAction.ACCELERATE: ["Trending position achieved", "Influencer pickup confirmed"],
            StrategyAction.MONITOR: ["No escalation required", "Alert thresholds not breached"],
        }
        return metrics.get(action, ["Positive outcome achieved"])

    async def _get_executive_summary(
        self, recommendations: list[StrategyRecommendation]
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            immediate = [r for r in recommendations if r.priority == StrategyPriority.IMMEDIATE]
            req = ModelRequest(
                prompt=f"Strategy summary: {len(recommendations)} narratives, {len(immediate)} immediate actions needed",
                task_type="narrative_strategy",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            immediate_count = sum(1 for r in recommendations if r.priority == StrategyPriority.IMMEDIATE)
            actions = list({r.action.value for r in recommendations})
            return (
                f"Strategic analysis complete: {len(recommendations)} narratives evaluated. "
                f"{immediate_count} require immediate action. "
                f"Primary strategies: {', '.join(actions[:3])}."
            )
