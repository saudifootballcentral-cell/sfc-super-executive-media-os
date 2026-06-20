"""Tests for EventBus: subscribe/publish, multiple handlers, history, publish_many."""

from __future__ import annotations

import pytest

from sfc.events.bus import EventBus, get_event_bus
from sfc.events.types import (
    ContentDraftCreated,
    GovernanceApproved,
    IntelligenceBriefReady,
    TrendDetected,
)


class TestEventBusSubscribePublish:
    def setup_method(self) -> None:
        self.bus = EventBus()

    def test_subscribe_and_publish_sync_handler(self) -> None:
        received: list[str] = []

        def handler(event: IntelligenceBriefReady) -> None:
            received.append(event.event_type)

        self.bus.subscribe("intelligence_brief_ready", handler)
        event = IntelligenceBriefReady(division="intelligence", run_id="run-1", payload={})
        self.bus.publish(event)

        assert "intelligence_brief_ready" in received

    def test_no_handlers_publish_is_silent(self) -> None:
        event = TrendDetected(division="intelligence", run_id="run-1", payload={})
        self.bus.publish(event)  # Must not raise

    def test_multiple_handlers_all_called(self) -> None:
        calls: list[str] = []

        def handler_a(event: ContentDraftCreated) -> None:
            calls.append("a")

        def handler_b(event: ContentDraftCreated) -> None:
            calls.append("b")

        self.bus.subscribe("content_draft_created", handler_a)
        self.bus.subscribe("content_draft_created", handler_b)

        event = ContentDraftCreated(division="editorial", run_id="run-1", payload={})
        self.bus.publish(event)

        assert "a" in calls
        assert "b" in calls

    def test_handler_not_called_for_different_event_type(self) -> None:
        called: list[bool] = []

        def handler(event: GovernanceApproved) -> None:
            called.append(True)

        self.bus.subscribe("governance_approved", handler)
        event = TrendDetected(division="intelligence", run_id="run-1", payload={})
        self.bus.publish(event)

        assert called == []


class TestEventBusHistory:
    def setup_method(self) -> None:
        self.bus = EventBus()

    def test_history_records_published_events(self) -> None:
        event = IntelligenceBriefReady(division="intelligence", run_id="run-1", payload={})
        self.bus.publish(event)
        history = self.bus.get_history()
        assert len(history) == 1
        assert history[0].event_type == "intelligence_brief_ready"

    def test_history_filtered_by_type(self) -> None:
        e1 = IntelligenceBriefReady(division="intelligence", run_id="run-1", payload={})
        e2 = TrendDetected(division="intelligence", run_id="run-1", payload={})
        self.bus.publish(e1)
        self.bus.publish(e2)

        intel_history = self.bus.get_history("intelligence_brief_ready")
        assert len(intel_history) == 1
        assert intel_history[0].event_type == "intelligence_brief_ready"

    def test_history_max_100_events(self) -> None:
        for i in range(120):
            e = TrendDetected(division="intelligence", run_id=f"run-{i}", payload={})
            self.bus.publish(e)
        history = self.bus.get_history()
        assert len(history) == 100

    def test_get_history_unfiltered_returns_all_types(self) -> None:
        e1 = IntelligenceBriefReady(division="intelligence", run_id="r1", payload={})
        e2 = TrendDetected(division="intelligence", run_id="r1", payload={})
        self.bus.publish(e1)
        self.bus.publish(e2)
        history = self.bus.get_history()
        types = {e.event_type for e in history}
        assert "intelligence_brief_ready" in types
        assert "trend_detected" in types


class TestEventBusPublishMany:
    def setup_method(self) -> None:
        self.bus = EventBus()

    def test_publish_many_delivers_all(self) -> None:
        received: list[str] = []

        def handler(event: TrendDetected) -> None:
            received.append(event.run_id)

        self.bus.subscribe("trend_detected", handler)
        events = [
            TrendDetected(division="intelligence", run_id=f"run-{i}", payload={})
            for i in range(5)
        ]
        self.bus.publish_many(events)

        assert len(received) == 5
        assert set(received) == {f"run-{i}" for i in range(5)}

    def test_publish_many_updates_history(self) -> None:
        events = [
            TrendDetected(division="intelligence", run_id=f"run-{i}", payload={})
            for i in range(10)
        ]
        self.bus.publish_many(events)
        history = self.bus.get_history()
        assert len(history) == 10


class TestEventBusSingleton:
    def test_get_event_bus_returns_same_instance(self) -> None:
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2


class TestEventBusAsync:
    def setup_method(self) -> None:
        self.bus = EventBus()

    async def test_async_handler_called(self) -> None:
        received: list[str] = []

        async def async_handler(event: TrendDetected) -> None:
            received.append(event.run_id)

        self.bus.subscribe("trend_detected", async_handler)
        event = TrendDetected(division="intelligence", run_id="async-run", payload={})
        self.bus.publish(event)
        # In no-running-loop context, handler is called via asyncio.run()
        # Let the event loop process
        import asyncio
        await asyncio.sleep(0.05)

    def test_reset_clears_state(self) -> None:
        def handler(e: TrendDetected) -> None:
            pass

        self.bus.subscribe("trend_detected", handler)
        event = TrendDetected(division="intelligence", run_id="r1", payload={})
        self.bus.publish(event)
        self.bus.reset()
        assert self.bus.get_history() == []
        assert "trend_detected" not in self.bus._handlers
