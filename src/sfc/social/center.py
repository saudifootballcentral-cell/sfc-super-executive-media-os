"""Social Intelligence Center — orchestrates all social intelligence services."""

from __future__ import annotations

import logging
from typing import Any

from sfc.social.audience.service import AudienceIntelligenceService, get_audience_service
from sfc.social.influencer.service import InfluencerIntelligenceService, get_influencer_service
from sfc.social.knowledge.service import SocialKnowledgeLayer, get_knowledge_layer
from sfc.social.narrative.service import NarrativeIntelligenceService, get_narrative_service
from sfc.social.opportunity.service import OpportunityDetectionEngine, get_opportunity_engine
from sfc.social.sentiment.service import FanSentimentService, get_sentiment_service
from sfc.social.trend_radar.service import TrendRadarService, get_trend_radar
from sfc.social.virality.service import ViralityPredictionEngine, get_virality_engine
from sfc.social.war_room.service import SocialWarRoomService, get_war_room_service

logger = logging.getLogger("sfc.social.center")

_singleton: "SocialIntelligenceCenter | None" = None


def get_social_center() -> "SocialIntelligenceCenter":
    global _singleton
    if _singleton is None:
        _singleton = SocialIntelligenceCenter()
    return _singleton


class SocialIntelligenceCenter:
    """Master orchestrator for all social intelligence operations."""

    def __init__(self) -> None:
        self._trend_radar: TrendRadarService = get_trend_radar()
        self._narrative: NarrativeIntelligenceService = get_narrative_service()
        self._sentiment: FanSentimentService = get_sentiment_service()
        self._influencer: InfluencerIntelligenceService = get_influencer_service()
        self._virality: ViralityPredictionEngine = get_virality_engine()
        self._audience: AudienceIntelligenceService = get_audience_service()
        self._war_room: SocialWarRoomService = get_war_room_service()
        self._opportunity: OpportunityDetectionEngine = get_opportunity_engine()
        self._knowledge: SocialKnowledgeLayer = get_knowledge_layer()

    @property
    def trend_radar(self) -> TrendRadarService:
        return self._trend_radar

    @property
    def narrative(self) -> NarrativeIntelligenceService:
        return self._narrative

    @property
    def sentiment(self) -> FanSentimentService:
        return self._sentiment

    @property
    def influencer(self) -> InfluencerIntelligenceService:
        return self._influencer

    @property
    def virality(self) -> ViralityPredictionEngine:
        return self._virality

    @property
    def audience(self) -> AudienceIntelligenceService:
        return self._audience

    @property
    def war_room(self) -> SocialWarRoomService:
        return self._war_room

    @property
    def opportunity(self) -> OpportunityDetectionEngine:
        return self._opportunity

    @property
    def knowledge(self) -> SocialKnowledgeLayer:
        return self._knowledge

    async def run_full_scan(
        self,
        topics: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a full social intelligence scan across all engines."""
        ctx = context or {}
        logger.info("[SocialCenter] Starting full social intelligence scan")

        # Trend Radar
        trend_snapshot = await self._trend_radar.scan(topics)
        trend_data = trend_snapshot.to_dict()
        logger.info("[SocialCenter] Trend scan complete — %d trends tracked", trend_snapshot.total_tracked)

        # Narrative Intelligence
        narratives = await self._narrative.detect_narratives(
            topics=topics, trend_data=trend_data
        )
        narrative_report = await self._narrative.generate_report(narratives)
        narrative_data = narrative_report.to_dict()

        # Fan Sentiment
        sentiment_targets = await self._sentiment.analyze(context=ctx)
        fan_pulse = await self._sentiment.generate_fan_pulse_report(sentiment_targets)
        sentiment_data = fan_pulse.to_dict()

        # Influencer Intelligence
        influencer_profiles = await self._influencer.scan()
        influencer_report = await self._influencer.generate_report(influencer_profiles)
        influencer_data = influencer_report.to_dict()

        # Audience Intelligence
        audience_profile = await self._audience.analyze()
        audience_report = await self._audience.generate_report(audience_profile)
        audience_data = audience_report.to_dict()

        # Opportunity Detection
        opportunities = await self._opportunity.detect(
            trend_data=trend_data,
            narrative_data=narrative_data,
            sentiment_data=sentiment_data,
            audience_data={"total_audience": audience_profile.total_audience},
        )
        opportunity_report = await self._opportunity.generate_report(opportunities)
        opportunity_data = opportunity_report.to_dict()

        # Update Knowledge Layer
        for trend in trend_snapshot.breaking_trends + trend_snapshot.emerging_trends:
            if isinstance(trend, dict):
                self._knowledge.ingest_from_trend(trend)

        knowledge_snapshot = self._knowledge.get_snapshot()

        # War Room evaluation
        war_room_alerts: list[dict[str, Any]] = []
        sentiment_alerts = await self._sentiment.get_alerts()
        if sentiment_alerts:
            from sfc.social.war_room.models import SocialWarRoomTrigger
            state = await self._war_room.activate(
                trigger=SocialWarRoomTrigger.SENTIMENT_CRISIS,
                context={"alerts": sentiment_alerts},
            )
            war_room_report = await self._war_room.generate_report(state)
            war_room_alerts.append(war_room_report.to_dict())

        logger.info("[SocialCenter] Full scan complete")

        return {
            "trend_radar": trend_data,
            "narrative_intelligence": narrative_data,
            "fan_sentiment": sentiment_data,
            "influencer_intelligence": influencer_data,
            "audience_intelligence": audience_data,
            "opportunity_detections": opportunity_data,
            "knowledge_snapshot": knowledge_snapshot.to_dict(),
            "war_room_alerts": war_room_alerts,
            "scan_complete": True,
        }

    async def get_status(self) -> dict[str, Any]:
        """Return current status of all social intelligence services."""
        return {
            "trend_radar": {"cached_trends": len(self._trend_radar._trends)},
            "narrative": {"cached_narratives": len(self._narrative._narratives)},
            "sentiment": {"tracked_entities": len(self._sentiment._targets)},
            "influencer": {"tracked_influencers": len(self._influencer._influencers)},
            "virality": {"forecast_history": len(self._virality._forecasts)},
            "audience": {"profile_ready": self._audience._profile is not None},
            "war_room": {"active_rooms": len(self._war_room.get_active_rooms())},
            "opportunity": {"detected_opportunities": len(self._opportunity._opportunities)},
            "knowledge": self._knowledge.get_snapshot().to_dict(),
        }
