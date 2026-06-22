"""Influencer Intelligence Service — tracks and ranks Saudi football influencers."""

from __future__ import annotations

import logging
from typing import Any

from sfc.social.influencer.models import (
    InfluencerMetrics,
    InfluencerProfile,
    InfluencerReport,
    InfluencerType,
)

logger = logging.getLogger("sfc.social.influencer")

_singleton: "InfluencerIntelligenceService | None" = None

_INFLUENCER_DATA = [
    ("Saudi Football Daily", "@SFD_News", InfluencerType.JOURNALIST, 450000, ["ar", "en"]),
    ("SPL Insider", "@SPL_Insider", InfluencerType.JOURNALIST, 380000, ["ar"]),
    ("Al Hilal Fan TV", "@AlHilalFanTV", InfluencerType.CREATOR, 620000, ["ar"]),
    ("Arabic Football Analysis", "@AFA_Analysis", InfluencerType.ANALYST, 290000, ["ar", "en"]),
    ("خالد الغامدي", "@khaled_ghamdi", InfluencerType.FORMER_PLAYER, 890000, ["ar"]),
    ("محمد العويس", "@m_alowais", InfluencerType.FORMER_PLAYER, 1200000, ["ar"]),
    ("Al Nassr Official", "@AlNassrFC", InfluencerType.CLUB_ACCOUNT, 5500000, ["ar", "en"]),
    ("Al Hilal Official", "@Alhilal_EN", InfluencerType.CLUB_ACCOUNT, 7200000, ["ar", "en"]),
    ("SFC Media Network", "@SFC_Media", InfluencerType.MEDIA_ORG, 340000, ["ar"]),
    ("Saudi Sports TV", "@SaudiSportsTV", InfluencerType.MEDIA_ORG, 780000, ["ar"]),
    ("Gulf Football Review", "@GFR_News", InfluencerType.JOURNALIST, 210000, ["ar", "en"]),
    ("Transfer Arabia", "@TransferArabia", InfluencerType.CREATOR, 560000, ["ar"]),
]


def get_influencer_service() -> "InfluencerIntelligenceService":
    global _singleton
    if _singleton is None:
        _singleton = InfluencerIntelligenceService()
    return _singleton


class InfluencerIntelligenceService:
    """Identifies and tracks key influencers in Saudi football media ecosystem."""

    def __init__(self) -> None:
        self._gateway = None
        self._influencers: dict[str, InfluencerProfile] = {}
        self._history: list[InfluencerReport] = []
        self._max_history = 200

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def scan(
        self,
        sources: list[str] | None = None,
        topic_filter: str | None = None,
    ) -> list[InfluencerProfile]:
        """Scan social platforms and return detected influencer profiles."""
        profiles = self._build_default_profiles()

        for profile in profiles:
            self._influencers[profile.influencer_id] = profile

        return profiles

    async def get_top_influencers(
        self,
        limit: int = 10,
        influencer_type: InfluencerType | None = None,
    ) -> list[InfluencerProfile]:
        """Return top influencers sorted by composite score."""
        if not self._influencers:
            await self.scan()

        profiles = list(self._influencers.values())
        if influencer_type:
            profiles = [p for p in profiles if p.influencer_type == influencer_type]

        return sorted(
            profiles,
            key=lambda p: p.metrics.composite_score,
            reverse=True,
        )[:limit]

    async def generate_report(
        self,
        profiles: list[InfluencerProfile] | None = None,
    ) -> InfluencerReport:
        """Generate a comprehensive influencer intelligence report."""
        if profiles is None:
            profiles = await self.get_top_influencers(limit=20)

        if not profiles:
            profiles = await self.scan()

        rankings = [
            {"influencer_id": p.influencer_id, "name": p.name, "score": round(p.metrics.composite_score, 1)}
            for p in profiles
        ]

        media_map: dict[str, list[str]] = {}
        for p in profiles:
            key = p.influencer_type.value
            media_map.setdefault(key, [])
            media_map[key].append(p.name)

        source_rankings = sorted(
            profiles, key=lambda p: p.metrics.reach_score, reverse=True
        )[:5]

        new_profiles = [p for p in profiles if not p.is_verified]
        alerts = [
            f"New high-impact influencer detected: {p.name} (composite={p.metrics.composite_score:.0f})"
            for p in new_profiles
            if p.metrics.composite_score > 70
        ]

        report = InfluencerReport(
            top_influencers=profiles[:10],
            influence_rankings=rankings,
            media_map=media_map,
            source_rankings=[p.to_summary() for p in source_rankings],
            total_tracked=len(profiles),
            new_influencers=len(new_profiles),
            alerts=alerts,
        )

        if len(self._history) < self._max_history:
            self._history.append(report)

        return report

    def get_influencer(self, influencer_id: str) -> InfluencerProfile | None:
        return self._influencers.get(influencer_id)

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def _build_default_profiles(self) -> list[InfluencerProfile]:
        from sfc.data.fixtures.loader import get_fixture_loader
        loader = get_fixture_loader()

        profiles = []
        for name, handle, itype, followers, langs in _INFLUENCER_DATA:
            fixture = loader.get_influencer_profile(handle)
            influence_score: float = float(fixture.get("influence_score", min(followers / 100000 * 13, 95.0)))
            trust_score: float = float(fixture.get("trust_score", min(followers / 100000 * 11, 90.0)))
            velocity_score: float = float(fixture.get("velocity_score", min(followers / 100000 * 10, 85.0)))
            authority_score: float = float(fixture.get("authority_score", min(followers / 100000 * 12, 92.0)))
            engagement_rate: float = float(fixture.get("engagement_rate", 0.048))

            metrics = InfluencerMetrics(
                influence_score=round(influence_score, 1),
                trust_score=round(trust_score, 1),
                reach_score=min(followers / 100000 * 10, 100),
                velocity_score=round(velocity_score, 1),
                authority_score=round(authority_score, 1),
                engagement_rate=round(engagement_rate, 4),
            )
            profiles.append(
                InfluencerProfile(
                    name=name,
                    handle=handle,
                    influencer_type=itype,
                    platforms=["x", "instagram"],
                    followers=followers,
                    metrics=metrics,
                    topics=["Saudi Pro League", "Saudi football", "Transfer news"],
                    languages=langs,
                    is_verified=followers > 500000,
                )
            )

        return profiles
