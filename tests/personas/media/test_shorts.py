"""Tests for ShortsPersona."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.personas.media.shorts.service import ShortsPersona


class TestShortsPersona:
    def setup_method(self):
        get_event_bus().reset()

    async def test_health_check(self):
        persona = ShortsPersona()
        health = persona.health_check()
        assert health["status"] == "healthy"
        assert health["persona_id"] == ShortsPersona.PERSONA_ID

    async def test_generate_insight(self):
        persona = ShortsPersona()
        insight = await persona.generate_insight({"task_type": "test", "run_id": "test-run-01"})
        assert insight.persona_id == ShortsPersona.PERSONA_ID
        assert len(insight.key_recommendations) > 0
        assert insight.persona_name == ShortsPersona.PERSONA_NAME

    async def test_platform_field(self):
        persona = ShortsPersona()
        insight = await persona.generate_insight({})
        assert insight.platform == ShortsPersona.PERSONA_PLATFORM

    async def test_analyze(self):
        persona = ShortsPersona()
        result = await persona.analyze({"test": True})
        assert isinstance(result, dict)
