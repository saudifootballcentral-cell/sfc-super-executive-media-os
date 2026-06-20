"""Tests for TransferPersona."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.personas.sports.transfer.service import TransferPersona


class TestTransferPersona:
    def setup_method(self):
        get_event_bus().reset()

    async def test_health_check(self):
        persona = TransferPersona()
        health = persona.health_check()
        assert health["status"] == "healthy"
        assert health["persona_id"] == TransferPersona.PERSONA_ID

    async def test_generate_insight(self):
        persona = TransferPersona()
        insight = await persona.generate_insight({"task_type": "test", "run_id": "test-run-01"})
        assert insight.persona_id == TransferPersona.PERSONA_ID
        assert len(insight.key_findings) > 0
        assert 0 < insight.confidence_score <= 100

    async def test_insight_published_event(self):
        persona = TransferPersona()
        bus = get_event_bus()
        await persona.generate_insight({"task_type": "test"})
        history = bus.get_history("persona_insight_generated")
        assert len(history) > 0

    async def test_analyze(self):
        persona = TransferPersona()
        result = await persona.analyze({"test": True})
        assert isinstance(result, dict)
