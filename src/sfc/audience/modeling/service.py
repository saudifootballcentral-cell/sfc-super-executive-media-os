"""Audience Modeling Engine — builds digital twins for Saudi football audience segments."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.audience.modeling.models import (
    AudienceDigitalTwin,
    AudienceInfluenceModel,
    AudienceModelReport,
    AudienceType,
    BehaviorModel,
    BehaviorPattern,
    ReactionModel,
)

logger = logging.getLogger("sfc.audience.modeling")

_singleton: "AudienceModelingEngine | None" = None


def get_audience_modeling_engine() -> "AudienceModelingEngine":
    global _singleton
    if _singleton is None:
        _singleton = AudienceModelingEngine()
    return _singleton


class AudienceModelingEngine:
    """Creates and maintains audience digital twins for behavioral modeling."""

    def __init__(self) -> None:
        self._gateway = None
        self._twins: dict[str, AudienceDigitalTwin] = {}
        self._history: list[AudienceModelReport] = []
        self._max_history = 100

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def build_models(
        self,
        audience_types: list[AudienceType] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[AudienceDigitalTwin]:
        """Build digital twins for specified audience types."""
        types = audience_types or list(AudienceType)
        twins: list[AudienceDigitalTwin] = []

        for audience_type in types:
            twin = self._build_twin(audience_type, context or {})
            self._twins[twin.twin_id] = twin
            twins.append(twin)

        return twins

    async def generate_report(
        self, twins: list[AudienceDigitalTwin] | None = None
    ) -> AudienceModelReport:
        """Generate a comprehensive audience model report."""
        if twins is None:
            twins = list(self._twins.values())
        if not twins:
            twins = await self.build_models()

        total = sum(t.size for t in twins)
        dominant = max(twins, key=lambda t: t.size, default=twins[0] if twins else None)

        key_insights = [
            f"{dominant.name if dominant else 'Fan'} segment dominates with {dominant.size:,} audience" if dominant else "",
            f"Average narrative adoption rate: {sum(t.narrative_adoption_rate for t in twins)/max(len(twins),1):.0f}%",
            f"Highest engagement: {max(twins, key=lambda t: t.behavior_model.engagement_rate, default=twins[0] if twins else None).name if twins else 'N/A'}",
        ]

        ai_analysis = await self._get_ai_analysis(twins, total)

        report = AudienceModelReport(
            digital_twins=twins,
            total_modeled_audience=total,
            dominant_type=dominant.audience_type if dominant else AudienceType.FAN,
            key_insights=[i for i in key_insights if i],
            ai_analysis=ai_analysis,
        )

        if len(self._history) < self._max_history:
            self._history.append(report)

        return report

    def get_twin(self, twin_id: str) -> AudienceDigitalTwin | None:
        return self._twins.get(twin_id)

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def _build_twin(
        self, audience_type: AudienceType, context: dict[str, Any]
    ) -> AudienceDigitalTwin:
        configs = {
            AudienceType.FAN: ("Saudi Football Fans", 3_500_000, BehaviorPattern.ACTIVE_ENGAGER, 0.08, 0.82),
            AudienceType.SUPPORTER: ("Club Supporters", 1_200_000, BehaviorPattern.CONTENT_SHARER, 0.12, 0.88),
            AudienceType.CASUAL_FOLLOWER: ("Casual Followers", 4_800_000, BehaviorPattern.PASSIVE_CONSUMER, 0.03, 0.45),
            AudienceType.JOURNALIST: ("Journalists", 12_000, BehaviorPattern.OPINION_LEADER, 0.25, 0.70),
            AudienceType.INFLUENCER: ("Influencers", 8_500, BehaviorPattern.TREND_AMPLIFIER, 0.35, 0.65),
            AudienceType.SPONSOR: ("Sponsors", 2_200, BehaviorPattern.BRAND_ADVOCATE, 0.18, 0.90),
            AudienceType.EXECUTIVE: ("Football Executives", 1_800, BehaviorPattern.OPINION_LEADER, 0.15, 0.95),
        }

        name, base_size, pattern, engagement, loyalty = configs.get(
            audience_type, ("Unknown", 100000, BehaviorPattern.PASSIVE_CONSUMER, 0.05, 0.60)
        )
        size = int(base_size * random.uniform(0.85, 1.15))
        engagement_pct = engagement * random.uniform(0.8, 1.2) * 100

        behavior = BehaviorModel(
            primary_pattern=pattern,
            engagement_rate=round(engagement_pct, 1),
            share_propensity=round(random.uniform(20, 70), 1),
            comment_propensity=round(random.uniform(15, 55), 1),
            narrative_adoption_speed=round(random.uniform(30, 80), 1),
            platform_loyalty=round(loyalty * 100, 1),
            sentiment_volatility=round(random.uniform(10, 40), 1),
            peak_activity_hours=[20, 21, 22, 9, 17],
        )

        reaction = ReactionModel(
            positive_content_response=round(random.uniform(60, 90), 1),
            negative_content_response=round(random.uniform(10, 40), 1),
            controversy_sensitivity=round(random.uniform(20, 70), 1),
            transfer_news_response=round(random.uniform(70, 95), 1),
            match_result_response=round(random.uniform(75, 98), 1),
            player_scandal_response=round(random.uniform(50, 85), 1),
        )

        influence = AudienceInfluenceModel(
            influenced_by=["@SPL_EN", "@AlHilalFC", "@SaudiNationalTeam"],
            influenced_platforms=["x", "instagram", "tiktok"],
            influence_susceptibility=round(random.uniform(30, 70), 1),
            peer_influence_weight=round(random.uniform(30, 60), 1),
            media_influence_weight=round(random.uniform(30, 70), 1),
            official_source_trust=round(random.uniform(50, 90), 1),
        )

        return AudienceDigitalTwin(
            audience_type=audience_type,
            name=name,
            description=f"Digital twin for Saudi football {name.lower()}",
            size=size,
            behavior_model=behavior,
            reaction_model=reaction,
            influence_model=influence,
            preferred_platforms=["x", "instagram", "tiktok"],
            preferred_content_types=["match highlights", "transfer news", "analysis"],
            top_interests=["Saudi Pro League", "National Team", "International Stars"],
            languages=["ar", "en"],
            avg_session_minutes=round(random.uniform(4, 18), 1),
            monthly_growth_rate=round(random.uniform(2, 20), 1),
            retention_rate=round(loyalty * 100, 1),
            narrative_adoption_rate=round(behavior.narrative_adoption_speed, 1),
        )

    async def _get_ai_analysis(
        self, twins: list[AudienceDigitalTwin], total: int
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Saudi football audience model: {total:,} total across {len(twins)} types",
                task_type="audience_modeling",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            top = max(twins, key=lambda t: t.behavior_model.engagement_rate, default=None)
            return (
                f"Modeled {total:,} audience across {len(twins)} segments. "
                f"Highest engagement: {top.name if top else 'N/A'} "
                f"({top.behavior_model.engagement_rate:.1f}% rate)."
            )
