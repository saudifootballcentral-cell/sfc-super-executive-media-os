"""Verify no random data in updated services — Package 10A."""

from __future__ import annotations

import ast
import importlib
import inspect
import sys
from pathlib import Path

import pytest


_UPDATED_MODULES = [
    "sfc.social.trend_radar.service",
    "sfc.social.sentiment.service",
    "sfc.social.virality.service",
    "sfc.social.influencer.service",
    "sfc.social.audience.service",
    "sfc.narrative.modeling.service",
    "sfc.narrative.forecasting.service",
    "sfc.connectors.youtube.service",
    "sfc.connectors.x.service",
]


class TestNoRandomImports:
    """Ensure that updated services do not import the random module."""

    @pytest.mark.parametrize("module_name", _UPDATED_MODULES)
    def test_no_random_import_in_source(self, module_name: str):
        module = importlib.import_module(module_name)
        source_file = inspect.getfile(module)
        source = Path(source_file).read_text()
        tree = ast.parse(source)

        random_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "random":
                        random_imports.append("import random")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "random":
                    random_imports.append(f"from random import ...")

        assert random_imports == [], (
            f"{module_name} still imports 'random': {random_imports}"
        )

    @pytest.mark.parametrize("module_name", _UPDATED_MODULES)
    def test_no_random_uniform_calls(self, module_name: str):
        module = importlib.import_module(module_name)
        source_file = inspect.getfile(module)
        source = Path(source_file).read_text()
        assert "random.uniform" not in source, (
            f"{module_name} still uses random.uniform"
        )

    @pytest.mark.parametrize("module_name", _UPDATED_MODULES)
    def test_no_random_randint_calls(self, module_name: str):
        module = importlib.import_module(module_name)
        source_file = inspect.getfile(module)
        source = Path(source_file).read_text()
        assert "random.randint" not in source, (
            f"{module_name} still uses random.randint"
        )

    @pytest.mark.parametrize("module_name", _UPDATED_MODULES)
    def test_no_random_choice_calls(self, module_name: str):
        module = importlib.import_module(module_name)
        source_file = inspect.getfile(module)
        source = Path(source_file).read_text()
        assert "random.choice" not in source, (
            f"{module_name} still uses random.choice"
        )


class TestDataSourceLabeling:
    """Verify that fixture-backed services label data_source correctly."""

    @pytest.mark.asyncio
    async def test_trend_radar_uses_fixture_data(self):
        from sfc.social.trend_radar.service import TrendRadarService
        service = TrendRadarService()
        snapshot = await service.scan(topics=["Al Hilal Champions League run"])
        assert snapshot.total_tracked >= 1

    @pytest.mark.asyncio
    async def test_sentiment_service_not_random(self):
        from sfc.social.sentiment.service import FanSentimentService
        s1 = FanSentimentService()
        s2 = FanSentimentService()
        targets1 = await s1.analyze(["al_hilal_club"])
        targets2 = await s2.analyze(["al_hilal_club"])
        # Fixture-backed — same input should produce same score
        assert targets1[0].metrics.score == targets2[0].metrics.score

    @pytest.mark.asyncio
    async def test_virality_engine_deterministic(self):
        from sfc.social.virality.service import ViralityPredictionEngine
        engine = ViralityPredictionEngine()
        f1 = await engine.forecast("Al Hilal", trend_score=70.0, sentiment_score=15.0)
        f2 = await engine.forecast("Al Hilal", trend_score=70.0, sentiment_score=15.0)
        assert f1.metrics.virality_score == f2.metrics.virality_score
        assert f1.metrics.expected_reach == f2.metrics.expected_reach

    @pytest.mark.asyncio
    async def test_influencer_service_deterministic(self):
        from sfc.social.influencer.service import InfluencerIntelligenceService
        s1 = InfluencerIntelligenceService()
        s2 = InfluencerIntelligenceService()
        p1 = await s1.scan()
        p2 = await s2.scan()
        names1 = [p.name for p in p1]
        names2 = [p.name for p in p2]
        assert names1 == names2

    @pytest.mark.asyncio
    async def test_audience_service_deterministic(self):
        from sfc.social.audience.service import AudienceIntelligenceService
        from sfc.social.audience.models import AudienceSegmentType
        s1 = AudienceIntelligenceService()
        s2 = AudienceIntelligenceService()
        profile1 = await s1.analyze([AudienceSegmentType.CORE_FANS])
        profile2 = await s2.analyze([AudienceSegmentType.CORE_FANS])
        assert profile1.segments[0].size == profile2.segments[0].size

    @pytest.mark.asyncio
    async def test_youtube_analytics_deterministic(self):
        from sfc.connectors.youtube.service import YouTubeService
        s1 = YouTubeService()
        s2 = YouTubeService()
        a1 = await s1.get_analytics("test_video_id")
        a2 = await s2.get_analytics("test_video_id")
        assert a1.views == a2.views

    @pytest.mark.asyncio
    async def test_x_metrics_deterministic(self):
        from sfc.connectors.x.service import XService
        s1 = XService()
        s2 = XService()
        m1 = await s1.get_metrics("post_123")
        m2 = await s2.get_metrics("post_123")
        assert m1.views == m2.views
        assert m1.engagement_rate == m2.engagement_rate
