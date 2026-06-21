"""Tests for the AutonomousTriggerEngine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sfc.autonomous.trigger_engine import AutonomousTriggerEngine, TriggerEvent
from sfc.scheduler.triggers import TriggerCondition, TriggerConfig, TriggerType


class TestTriggerEvent:
    def test_creation(self):
        event = TriggerEvent(
            trigger_type=TriggerType.MANUAL,
            trigger_name="test_trigger",
        )
        assert event.event_id
        assert event.alert_sent is False
        assert event.acknowledged is False

    def test_context_snapshot_optional(self):
        event = TriggerEvent(
            trigger_type=TriggerType.CRISIS_DETECTED,
            trigger_name="crisis",
            context_snapshot={"session_total_usd": 55.0},
        )
        assert event.context_snapshot["session_total_usd"] == 55.0


class TestAutonomousTriggerEngine:
    def test_default_triggers_loaded(self):
        engine = AutonomousTriggerEngine()
        report = engine.get_trigger_report()
        assert report["total_triggers"] >= 4  # cost, crisis, audience, sponsor
        assert report["enabled_triggers"] >= 4

    def test_add_custom_trigger(self):
        engine = AutonomousTriggerEngine()
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="custom_test",
            job_task_type="custom_job",
        )
        trigger_id = engine.add_trigger(trigger)
        report = engine.get_trigger_report()
        assert report["total_triggers"] >= 5  # 4 defaults + 1 custom

    def test_remove_trigger(self):
        engine = AutonomousTriggerEngine()
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="removable",
            job_task_type="test",
        )
        trigger_id = engine.add_trigger(trigger)
        before = engine.get_trigger_report()["total_triggers"]
        result = engine.remove_trigger(trigger_id)
        assert result is True
        after = engine.get_trigger_report()["total_triggers"]
        assert after == before - 1

    def test_remove_nonexistent_trigger(self):
        engine = AutonomousTriggerEngine()
        assert engine.remove_trigger("nonexistent") is False

    @pytest.mark.asyncio
    async def test_evaluate_empty_context_crisis_fires(self):
        engine = AutonomousTriggerEngine()
        # Crisis trigger fires for any context (always condition)
        events = await engine.evaluate({})
        crisis_events = [e for e in events if e.trigger_type == TriggerType.CRISIS_DETECTED]
        assert len(crisis_events) == 1

    @pytest.mark.asyncio
    async def test_cost_threshold_fires_when_exceeded(self):
        engine = AutonomousTriggerEngine()
        # Override the cost total by mocking the condition field
        context = {"session_total_usd": 100.0}  # exceeds $50 threshold
        events = await engine.evaluate(context)
        cost_events = [e for e in events if e.trigger_type == TriggerType.COST_THRESHOLD_EXCEEDED]
        assert len(cost_events) == 1

    @pytest.mark.asyncio
    async def test_cost_threshold_does_not_fire_below_threshold(self):
        engine = AutonomousTriggerEngine()
        # First, fire it to set last_fired_at on the original trigger
        # Instead, let's add a new cost trigger with low threshold
        engine2 = AutonomousTriggerEngine()
        # Clear default triggers and add fresh one with no cooldown issue
        # The default cost trigger has cooldown=3600; fire once to set last_fired
        context_below = {"session_total_usd": 10.0}
        events = await engine2.evaluate(context_below)
        cost_events = [e for e in events if e.trigger_type == TriggerType.COST_THRESHOLD_EXCEEDED]
        assert len(cost_events) == 0

    @pytest.mark.asyncio
    async def test_audience_drop_fires_when_reach_low(self):
        engine = AutonomousTriggerEngine()
        context = {
            "analytics_report": {"estimated_reach": 5000},  # below 10k threshold
            "session_total_usd": 0.0,
        }
        events = await engine.evaluate(context)
        drop_events = [e for e in events if e.trigger_type == TriggerType.AUDIENCE_DROP_DETECTED]
        assert len(drop_events) == 1

    @pytest.mark.asyncio
    async def test_sponsor_opportunity_fires_when_high_value(self):
        engine = AutonomousTriggerEngine()
        context = {
            "revenue_summary": {"total_opportunity_usd": 15000.0},
            "session_total_usd": 0.0,
        }
        events = await engine.evaluate(context)
        sponsor_events = [e for e in events if e.trigger_type == TriggerType.REVENUE_OPPORTUNITY_DETECTED]
        assert len(sponsor_events) == 1

    @pytest.mark.asyncio
    async def test_cooldown_prevents_double_firing(self):
        engine = AutonomousTriggerEngine()
        context = {}
        # Fire once
        events1 = await engine.evaluate(context)
        crisis1 = [e for e in events1 if e.trigger_type == TriggerType.CRISIS_DETECTED]
        assert len(crisis1) == 1

        # Fire again immediately — cooldown should prevent
        events2 = await engine.evaluate(context)
        crisis2 = [e for e in events2 if e.trigger_type == TriggerType.CRISIS_DETECTED]
        assert len(crisis2) == 0

    @pytest.mark.asyncio
    async def test_evaluate_from_state(self):
        engine = AutonomousTriggerEngine()
        pipeline_state = {
            "analytics_report": {},
            "rejected_content": [],
            "errors": [],
            "task_type": "news",
        }
        events = await engine.evaluate_from_state(pipeline_state)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_fired_events_are_recorded(self):
        engine = AutonomousTriggerEngine()
        await engine.evaluate({})
        fired = engine.get_fired_events()
        assert len(fired) >= 1
        assert "event_id" in fired[0]
        assert "trigger_type" in fired[0]

    @pytest.mark.asyncio
    async def test_trigger_report_structure(self):
        engine = AutonomousTriggerEngine()
        await engine.evaluate({})
        report = engine.get_trigger_report()
        assert "total_triggers" in report
        assert "enabled_triggers" in report
        assert "total_fired" in report
        assert "triggers" in report
        assert report["total_fired"] >= 1

    @pytest.mark.asyncio
    async def test_custom_trigger_fires(self):
        engine = AutonomousTriggerEngine()
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="custom_fire",
            conditions=[TriggerCondition(condition_type="always")],
            job_task_type="custom",
            cooldown_seconds=0,
        )
        engine.add_trigger(trigger)
        events = await engine.evaluate({})
        custom_events = [e for e in events if e.trigger_name == "custom_fire"]
        assert len(custom_events) == 1

    @pytest.mark.asyncio
    async def test_context_sanitized_in_event(self):
        engine = AutonomousTriggerEngine()
        context = {}
        events = await engine.evaluate(context)
        for event in events:
            # All values in snapshot should be serializable primitives
            for v in event.context_snapshot.values():
                assert isinstance(v, (str, int, float, bool, type(None), dict, list))
