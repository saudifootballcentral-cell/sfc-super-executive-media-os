"""Integration tests for Media & Platform Personas."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.personas.media import register_media_personas
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.media.tiktok.service import TikTokPersona
from sfc.personas.media.instagram.service import InstagramPersona
from sfc.personas.media.youtube.service import YouTubePersona
from sfc.personas.media.x.service import XPersona
from sfc.personas.media.shorts.service import ShortsPersona
from sfc.personas.media.thumbnail.service import ThumbnailPersona
from sfc.personas.media.documentary.service import DocumentaryPersona
from sfc.personas.media.seo.service import SEOPersona


class TestMediaIntegration:
    def setup_method(self):
        get_event_bus().reset()

    async def test_register_all_media_personas(self):
        registry = PersonaRegistry()
        count = register_media_personas(registry)
        assert count == 15

    async def test_media_personas_in_registry(self):
        registry = PersonaRegistry()
        register_media_personas(registry)
        all_personas = registry.list_all()
        assert len(all_personas) >= 15

    async def test_tiktok_script_generation(self):
        persona = TikTokPersona()
        result = await persona.generate_script("Ronaldo to Al Nassr comeback", 30)
        assert "hook" in result
        assert result["duration_seconds"] == 30

    async def test_tiktok_hook_analysis(self):
        persona = TikTokPersona()
        result = await persona.analyze_hook("Nobody is talking about this Saudi football secret...")
        assert "overall_score" in result
        assert result["overall_score"] > 0

    async def test_youtube_episode_structure(self):
        persona = YouTubePersona()
        result = await persona.structure_episode("Al Hilal Season Review", 18)
        assert "structure" in result
        assert result["duration_min"] == 18

    async def test_x_thread_generation(self):
        persona = XPersona()
        result = await persona.generate_thread("Al Nassr transfer news", tweet_count=5)
        assert len(result["tweets"]) == 5

    async def test_viral_short_video_collaboration(self):
        tiktok = TikTokPersona()
        shorts = ShortsPersona()
        thumb = ThumbnailPersona()
        ctx = {"topic": "Salah transfer to SPL", "run_id": "collab-01"}
        t = await tiktok.generate_insight(ctx)
        s = await shorts.generate_insight(ctx)
        th = await thumb.generate_insight(ctx)
        assert all(i.persona_id for i in [t, s, th])

    async def test_documentary_package_collaboration(self):
        youtube = YouTubePersona()
        doc = DocumentaryPersona()
        seo = SEOPersona()
        ctx = {"title": "The Rise of Saudi Football", "topic": "Saudi football history"}
        y = await youtube.generate_insight(ctx)
        d = await doc.generate_insight(ctx)
        s = await seo.generate_insight(ctx)
        assert all(i.persona_id for i in [y, d, s])
