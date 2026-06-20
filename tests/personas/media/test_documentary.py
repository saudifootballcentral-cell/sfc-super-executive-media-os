"""Tests for DocumentaryPersona."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.personas.media.documentary.service import DocumentaryPersona


class TestDocumentaryPersona:
    def setup_method(self):
        get_event_bus().reset()

    async def test_health_check(self):
        persona = DocumentaryPersona()
        health = persona.health_check()
        assert health["status"] == "healthy"
        assert health["persona_id"] == DocumentaryPersona.PERSONA_ID

    async def test_generate_insight(self):
        persona = DocumentaryPersona()
        insight = await persona.generate_insight({"task_type": "test", "run_id": "test-run-01"})
        assert insight.persona_id == DocumentaryPersona.PERSONA_ID
        assert len(insight.key_recommendations) > 0
        assert insight.persona_name == DocumentaryPersona.PERSONA_NAME

    async def test_platform_field(self):
        persona = DocumentaryPersona()
        insight = await persona.generate_insight({})
        assert insight.platform == DocumentaryPersona.PERSONA_PLATFORM

    async def test_analyze(self):
        persona = DocumentaryPersona()
        result = await persona.analyze({"test": True})
        assert isinstance(result, dict)
