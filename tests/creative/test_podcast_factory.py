"""Tests for AI Podcast Factory (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.podcast.models import (
    PodcastEpisode,
    PodcastSegment,
    PodcastSegmentType,
    PodcastType,
)
from sfc.creative.podcast.service import PodcastFactoryService, get_podcast_factory_service


class TestPodcastModels:
    def test_podcast_segment_defaults(self):
        seg = PodcastSegment()
        assert seg.segment_id
        assert seg.segment_type == PodcastSegmentType.CONTENT

    def test_podcast_episode_to_dict(self):
        ep = PodcastEpisode(podcast_type=PodcastType.DAILY_SHOW, episode_title="Test")
        d = ep.to_dict()
        assert d["podcast_type"] == "daily_show"
        assert d["episode_title"] == "Test"

    def test_podcast_episode_to_summary(self):
        ep = PodcastEpisode(
            podcast_type=PodcastType.MATCH_RECAP,
            episode_title="SPL Round 10",
            episode_number=10,
        )
        summary = ep.to_summary()
        assert "match_recap" in summary
        assert "EP10" in summary

    def test_podcast_segment_to_dict(self):
        seg = PodcastSegment(segment_number=2, title="Analysis")
        d = seg.to_dict()
        assert d["segment_number"] == 2


class TestPodcastFactoryService:
    @pytest.mark.asyncio
    async def test_generate_daily_show(self):
        service = PodcastFactoryService()
        ep = await service.generate_episode(
            episode_title="SPL Daily Show Ep 1",
            podcast_type=PodcastType.DAILY_SHOW,
        )
        assert isinstance(ep, PodcastEpisode)
        assert ep.podcast_type == PodcastType.DAILY_SHOW

    @pytest.mark.asyncio
    async def test_segments_generated(self):
        service = PodcastFactoryService()
        ep = await service.generate_episode(
            episode_title="Test Episode",
            podcast_type=PodcastType.DAILY_SHOW,
        )
        assert len(ep.segments) >= 4

    @pytest.mark.asyncio
    async def test_episode_number_increments(self):
        service = PodcastFactoryService()
        ep1 = await service.generate_episode("Episode A", PodcastType.TACTICAL_SHOW)
        ep2 = await service.generate_episode("Episode B", PodcastType.TACTICAL_SHOW)
        assert ep2.episode_number > ep1.episode_number

    @pytest.mark.asyncio
    async def test_full_script_assembled(self):
        service = PodcastFactoryService()
        ep = await service.generate_episode("Script Test", PodcastType.DAILY_SHOW)
        assert ep.full_script != ""

    @pytest.mark.asyncio
    async def test_chapters_built(self):
        service = PodcastFactoryService()
        ep = await service.generate_episode("Chapter Test", PodcastType.MATCH_RECAP)
        assert len(ep.chapters) >= 3

    @pytest.mark.asyncio
    async def test_duration_positive(self):
        service = PodcastFactoryService()
        ep = await service.generate_episode("Duration Test", PodcastType.DAILY_SHOW)
        assert ep.total_duration_minutes > 0

    @pytest.mark.asyncio
    async def test_narratives_used(self):
        service = PodcastFactoryService()
        ep = await service.generate_episode(
            "Narrative Episode",
            PodcastType.TRANSFER_SHOW,
            narratives=["Ronaldo to Al Hilal rumour", "Transfer window deadline"],
        )
        assert ep.episode_title == "Narrative Episode"
        assert len(ep.tags) > 0

    def test_singleton(self):
        s1 = get_podcast_factory_service()
        s2 = get_podcast_factory_service()
        assert s1 is s2
