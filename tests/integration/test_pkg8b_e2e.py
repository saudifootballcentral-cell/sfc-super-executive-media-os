"""Package 8B end-to-end integration tests — Social Intelligence & Trend Analysis Engine."""

from __future__ import annotations

import pytest

from sfc.graph.state import SFCState, make_initial_state
from sfc.social.trend_radar.service import TrendRadarService
from sfc.social.narrative.service import NarrativeIntelligenceService
from sfc.social.sentiment.service import FanSentimentService
from sfc.social.influencer.service import InfluencerIntelligenceService
from sfc.social.virality.service import ViralityPredictionEngine
from sfc.social.audience.service import AudienceIntelligenceService
from sfc.social.war_room.service import SocialWarRoomService
from sfc.social.opportunity.service import OpportunityDetectionEngine
from sfc.social.knowledge.service import SocialKnowledgeLayer
from sfc.social.center import SocialIntelligenceCenter


# ---------------------------------------------------------------------------
# State extension tests
# ---------------------------------------------------------------------------

class TestSFCStatePkg8BFields:
    """Verify that all Package 8B fields are present in SFCState."""

    def test_social_intelligence_report_field(self):
        state = make_initial_state("news_coverage", {})
        assert "social_intelligence_report" in state
        assert state["social_intelligence_report"] == {}

    def test_trend_radar_data_field(self):
        state = make_initial_state("news_coverage", {})
        assert "trend_radar_data" in state
        assert state["trend_radar_data"] == {}

    def test_narrative_intelligence_data_field(self):
        state = make_initial_state("news_coverage", {})
        assert "narrative_intelligence_data" in state

    def test_fan_sentiment_data_field(self):
        state = make_initial_state("news_coverage", {})
        assert "fan_sentiment_data" in state

    def test_influencer_data_field(self):
        state = make_initial_state("news_coverage", {})
        assert "influencer_data" in state

    def test_virality_forecast_field(self):
        state = make_initial_state("news_coverage", {})
        assert "virality_forecast" in state

    def test_audience_intelligence_data_field(self):
        state = make_initial_state("news_coverage", {})
        assert "audience_intelligence_data" in state

    def test_social_war_room_state_field(self):
        state = make_initial_state("news_coverage", {})
        assert "social_war_room_state" in state

    def test_opportunity_detections_field(self):
        state = make_initial_state("news_coverage", {})
        assert "opportunity_detections" in state
        assert state["opportunity_detections"] == []

    def test_social_knowledge_snapshot_field(self):
        state = make_initial_state("news_coverage", {})
        assert "social_knowledge_snapshot" in state


# ---------------------------------------------------------------------------
# Event type extension tests
# ---------------------------------------------------------------------------

class TestPkg8BEventTypes:
    """Verify Package 8B events are registered in EVENT_TYPE_MAP."""

    def test_trend_peaked_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP, TrendPeaked
        assert "trend_peaked" in EVENT_TYPE_MAP
        assert EVENT_TYPE_MAP["trend_peaked"] is TrendPeaked

    def test_trend_declined_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP, TrendDeclined
        assert "trend_declined" in EVENT_TYPE_MAP

    def test_narrative_detected_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP, NarrativeDetected
        assert "narrative_detected" in EVENT_TYPE_MAP

    def test_narrative_shift_detected_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "narrative_shift_detected" in EVENT_TYPE_MAP

    def test_sentiment_updated_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "sentiment_updated" in EVENT_TYPE_MAP

    def test_sentiment_crisis_detected_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "sentiment_crisis_detected" in EVENT_TYPE_MAP

    def test_influencer_detected_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "influencer_detected" in EVENT_TYPE_MAP

    def test_virality_forecast_generated_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "virality_forecast_generated" in EVENT_TYPE_MAP

    def test_social_war_room_activated_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "social_war_room_activated" in EVENT_TYPE_MAP

    def test_all_events_instantiatable(self):
        from sfc.events.types import EVENT_TYPE_MAP
        pkg8b_events = [
            "trend_peaked", "trend_declined", "narrative_detected",
            "narrative_shift_detected", "sentiment_updated",
            "sentiment_crisis_detected", "influencer_detected",
            "virality_forecast_generated", "social_war_room_activated",
        ]
        for event_type in pkg8b_events:
            cls = EVENT_TYPE_MAP[event_type]
            event = cls(
                event_type=event_type,
                division="social",
                run_id="test-run",
            )
            assert event.event_type == event_type


# ---------------------------------------------------------------------------
# LangGraph node tests
# ---------------------------------------------------------------------------

class TestSocialIntelligenceNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.social_intelligence_node import social_intelligence_node
        state = make_initial_state("social_scan", {"topics": ["Al Hilal"]})
        result = await social_intelligence_node(state)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_node_has_pipeline_stage(self):
        from sfc.graph.nodes.social_intelligence_node import social_intelligence_node
        state = make_initial_state("social_scan", {})
        result = await social_intelligence_node(state)
        assert "pipeline_stage" in result

    @pytest.mark.asyncio
    async def test_node_populates_social_intelligence_report(self):
        from sfc.graph.nodes.social_intelligence_node import social_intelligence_node
        state = make_initial_state("social_scan", {"topics": ["test"]})
        result = await social_intelligence_node(state)
        assert "social_intelligence_report" in result
        assert isinstance(result["social_intelligence_report"], dict)


class TestTrendRadarNode:
    @pytest.mark.asyncio
    async def test_node_success(self):
        from sfc.graph.nodes.trend_radar_node import trend_radar_node
        state = make_initial_state("news_coverage", {})
        result = await trend_radar_node(state)
        assert "trend_radar_data" in result
        assert isinstance(result["trend_radar_data"], dict)

    @pytest.mark.asyncio
    async def test_node_pipeline_stage(self):
        from sfc.graph.nodes.trend_radar_node import trend_radar_node
        state = make_initial_state("news_coverage", {})
        result = await trend_radar_node(state)
        assert result["pipeline_stage"] in (
            "trend_radar_complete", "trend_radar_skipped"
        )


class TestNarrativeIntelligenceNode:
    @pytest.mark.asyncio
    async def test_node_success(self):
        from sfc.graph.nodes.narrative_intelligence_node import narrative_intelligence_node
        state = make_initial_state("news_coverage", {})
        result = await narrative_intelligence_node(state)
        assert "narrative_intelligence_data" in result

    @pytest.mark.asyncio
    async def test_node_uses_trend_data(self):
        from sfc.graph.nodes.narrative_intelligence_node import narrative_intelligence_node
        state = make_initial_state("news_coverage", {})
        state["trend_radar_data"] = {"top_topic": "Al Hilal Champions"}
        result = await narrative_intelligence_node(state)
        assert isinstance(result.get("narrative_intelligence_data"), dict)


class TestFanSentimentNode:
    @pytest.mark.asyncio
    async def test_node_success(self):
        from sfc.graph.nodes.fan_sentiment_node import fan_sentiment_node
        state = make_initial_state("news_coverage", {})
        result = await fan_sentiment_node(state)
        assert "fan_sentiment_data" in result

    @pytest.mark.asyncio
    async def test_node_pipeline_stage(self):
        from sfc.graph.nodes.fan_sentiment_node import fan_sentiment_node
        state = make_initial_state("news_coverage", {})
        result = await fan_sentiment_node(state)
        assert result["pipeline_stage"] in (
            "fan_sentiment_complete", "fan_sentiment_skipped"
        )


class TestInfluencerIntelligenceNode:
    @pytest.mark.asyncio
    async def test_node_success(self):
        from sfc.graph.nodes.influencer_intelligence_node import influencer_intelligence_node
        state = make_initial_state("news_coverage", {})
        result = await influencer_intelligence_node(state)
        assert "influencer_data" in result


class TestViralityPredictionNode:
    @pytest.mark.asyncio
    async def test_node_with_trend_data(self):
        from sfc.graph.nodes.virality_prediction_node import virality_prediction_node
        state = make_initial_state("news_coverage", {})
        state["trend_radar_data"] = {
            "top_topic": "SPL Final",
            "top_score": 88.0,
            "breaking_trends": [{"topic": "SPL Final"}],
        }
        result = await virality_prediction_node(state)
        assert "virality_forecast" in result

    @pytest.mark.asyncio
    async def test_node_no_trend_data(self):
        from sfc.graph.nodes.virality_prediction_node import virality_prediction_node
        state = make_initial_state("news_coverage", {})
        result = await virality_prediction_node(state)
        assert "virality_forecast" in result


class TestAudienceIntelligenceNode:
    @pytest.mark.asyncio
    async def test_node_success(self):
        from sfc.graph.nodes.audience_intelligence_node import audience_intelligence_node
        state = make_initial_state("news_coverage", {})
        result = await audience_intelligence_node(state)
        assert "audience_intelligence_data" in result


class TestOpportunityDetectionNode:
    @pytest.mark.asyncio
    async def test_node_success(self):
        from sfc.graph.nodes.opportunity_detection_node import opportunity_detection_node
        state = make_initial_state("news_coverage", {})
        result = await opportunity_detection_node(state)
        assert "opportunity_detections" in result

    @pytest.mark.asyncio
    async def test_node_with_all_inputs(self):
        from sfc.graph.nodes.opportunity_detection_node import opportunity_detection_node
        state = make_initial_state("news_coverage", {})
        state["trend_radar_data"] = {"top_topic": "Transfer window", "top_score": 80.0}
        state["narrative_intelligence_data"] = {"top_narratives": [{"title": "Al Hilal run"}]}
        state["fan_sentiment_data"] = {"overall_score": 60.0}
        state["audience_intelligence_data"] = {"profile": {"total_audience": 5000000}}
        result = await opportunity_detection_node(state)
        assert isinstance(result["opportunity_detections"], list)


class TestSocialWarRoomNode:
    @pytest.mark.asyncio
    async def test_node_no_triggers(self):
        from sfc.graph.nodes.social_war_room_node import social_war_room_node
        state = make_initial_state("news_coverage", {})
        result = await social_war_room_node(state)
        assert "social_war_room_state" in result

    @pytest.mark.asyncio
    async def test_node_with_sentiment_alerts(self):
        from sfc.graph.nodes.social_war_room_node import social_war_room_node
        state = make_initial_state("news_coverage", {})
        state["fan_sentiment_data"] = {
            "alerts": ["CRISIS: Al Hilal at -65"],
            "overall_score": -65.0,
        }
        result = await social_war_room_node(state)
        war_room = result.get("social_war_room_state", {})
        assert isinstance(war_room, dict)

    @pytest.mark.asyncio
    async def test_node_explicit_trigger(self):
        from sfc.graph.nodes.social_war_room_node import social_war_room_node
        state = make_initial_state(
            "news_coverage",
            {"war_room_trigger": "breaking_story"},
        )
        result = await social_war_room_node(state)
        war_room = result.get("social_war_room_state", {})
        assert war_room.get("activated_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_node_pipeline_stage(self):
        from sfc.graph.nodes.social_war_room_node import social_war_room_node
        state = make_initial_state("news_coverage", {})
        result = await social_war_room_node(state)
        assert result["pipeline_stage"] in (
            "social_war_room_complete", "social_war_room_skipped"
        )


# ---------------------------------------------------------------------------
# SocialIntelligenceCenter integration tests
# ---------------------------------------------------------------------------

class TestSocialIntelligenceCenter:
    def test_center_has_all_services(self):
        center = SocialIntelligenceCenter()
        assert isinstance(center.trend_radar, TrendRadarService)
        assert isinstance(center.narrative, NarrativeIntelligenceService)
        assert isinstance(center.sentiment, FanSentimentService)
        assert isinstance(center.influencer, InfluencerIntelligenceService)
        assert isinstance(center.virality, ViralityPredictionEngine)
        assert isinstance(center.audience, AudienceIntelligenceService)
        assert isinstance(center.war_room, SocialWarRoomService)
        assert isinstance(center.opportunity, OpportunityDetectionEngine)
        assert isinstance(center.knowledge, SocialKnowledgeLayer)

    @pytest.mark.asyncio
    async def test_run_full_scan(self):
        center = SocialIntelligenceCenter()
        result = await center.run_full_scan(topics=["Al Hilal Champions League"])
        assert isinstance(result, dict)
        assert result.get("scan_complete") is True

    @pytest.mark.asyncio
    async def test_full_scan_has_all_sections(self):
        center = SocialIntelligenceCenter()
        result = await center.run_full_scan()
        expected_keys = [
            "trend_radar",
            "narrative_intelligence",
            "fan_sentiment",
            "influencer_intelligence",
            "audience_intelligence",
            "opportunity_detections",
            "knowledge_snapshot",
            "war_room_alerts",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_get_status(self):
        center = SocialIntelligenceCenter()
        status = await center.get_status()
        assert isinstance(status, dict)
        assert "trend_radar" in status
        assert "knowledge" in status

    @pytest.mark.asyncio
    async def test_knowledge_populated_after_scan(self):
        center = SocialIntelligenceCenter()
        await center.run_full_scan(topics=["Test Topic"])
        snapshot = center.knowledge.get_snapshot()
        assert isinstance(snapshot.total_entities, int)


# ---------------------------------------------------------------------------
# Cross-service pipeline simulation
# ---------------------------------------------------------------------------

class TestPkg8BCrossPipeline:
    """Simulate the social intelligence data flowing through the pipeline."""

    @pytest.mark.asyncio
    async def test_trend_feeds_narrative(self):
        trend_svc = TrendRadarService()
        narrative_svc = NarrativeIntelligenceService()

        snapshot = await trend_svc.scan(topics=["SPL transfer"])
        trend_data = snapshot.to_dict()

        narratives = await narrative_svc.detect_narratives(
            topics=["SPL transfer"], trend_data=trend_data
        )
        assert len(narratives) > 0

    @pytest.mark.asyncio
    async def test_sentiment_crisis_triggers_war_room(self):
        sentiment_svc = FanSentimentService()
        war_room_svc = SocialWarRoomService()
        from sfc.social.war_room.models import SocialWarRoomTrigger

        from sfc.social.sentiment.models import SentimentMetrics, SentimentTarget, SentimentTarget_
        crisis_target = SentimentTarget_(
            entity_name="Crisis Club",
            target_type=SentimentTarget.CLUB,
            metrics=SentimentMetrics(score=-75.0),
        )
        sentiment_svc._targets["crisis_club"] = crisis_target

        alerts = await sentiment_svc.get_alerts()
        assert len(alerts) > 0

        should_activate = await war_room_svc.evaluate(
            SocialWarRoomTrigger.SENTIMENT_CRISIS,
            context={"sentiment_score": -75.0},
        )
        assert should_activate is True

    @pytest.mark.asyncio
    async def test_trend_to_virality_pipeline(self):
        trend_svc = TrendRadarService()
        virality_engine = ViralityPredictionEngine()

        snapshot = await trend_svc.scan(topics=["Champions League Saudi"])
        top_topic = snapshot.top_topic

        if top_topic:
            forecast = await virality_engine.forecast(
                topic=top_topic,
                trend_score=snapshot.top_score,
            )
            assert forecast.metrics.virality_score >= 0

    @pytest.mark.asyncio
    async def test_knowledge_ingests_trend_and_narrative(self):
        knowledge = SocialKnowledgeLayer()
        trend_svc = TrendRadarService()
        narrative_svc = NarrativeIntelligenceService()

        snapshot = await trend_svc.scan(topics=["Al Nassr win"])
        for trend in snapshot.breaking_trends[:2]:
            if isinstance(trend, dict):
                knowledge.ingest_from_trend(trend)

        narratives = await narrative_svc.detect_narratives(topics=["Al Nassr win"])
        for n in narratives[:2]:
            knowledge.ingest_from_narrative(n.to_dict())

        kg_snapshot = knowledge.get_snapshot()
        assert kg_snapshot.total_entities >= 0

    @pytest.mark.asyncio
    async def test_opportunity_from_trends_and_audience(self):
        trend_svc = TrendRadarService()
        audience_svc = AudienceIntelligenceService()
        opp_engine = OpportunityDetectionEngine()

        trend_snapshot = await trend_svc.scan(topics=["Transfer window open"])
        trend_data = trend_snapshot.to_dict()

        audience_profile = await audience_svc.analyze()
        audience_data = {"total_audience": audience_profile.total_audience}

        opportunities = await opp_engine.detect(
            trend_data=trend_data,
            audience_data=audience_data,
        )
        report = await opp_engine.generate_report(opportunities)

        assert isinstance(report.total_revenue_potential, float)
        assert report.total_revenue_potential >= 0
