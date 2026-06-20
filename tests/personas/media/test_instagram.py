"""Tests for InstagramPersona."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.personas.media.instagram.service import InstagramPersona


class TestInstagramPersona:
    def setup_method(self):
        get_event_bus().reset()

    async def test_health_check(self):
        persona = InstagramPersona()
        health = persona.health_check()
        assert health["status"] == "healthy"
        assert health["persona_id"] == InstagramPersona.PERSONA_ID

    async def test_generate_insight(self):
        persona = InstagramPersona()
        insight = await persona.generate_insight({"task_type": "test", "run_id": "test-run-01"})
        assert insight.persona_id == InstagramPersona.PERSONA_ID
        assert len(insight.key_recommendations) > 0
        assert insight.persona_name == InstagramPersona.PERSONA_NAME

    async def test_platform_field(self):
        persona = InstagramPersona()
        insight = await persona.generate_insight({})
        assert insight.platform == InstagramPersona.PERSONA_PLATFORM

    async def test_analyze(self):
        persona = InstagramPersona()
        result = await persona.analyze({"test": True})
        assert isinstance(result, dict)
