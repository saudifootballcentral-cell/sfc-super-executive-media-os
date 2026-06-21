"""Tests for Social War Room."""

from __future__ import annotations

import pytest

from sfc.social.war_room.models import (
    SocialWarRoomReport,
    SocialWarRoomState,
    SocialWarRoomTrigger,
    WarRoomPriority,
    WarRoomStatus,
)
from sfc.social.war_room.service import SocialWarRoomService, get_war_room_service


class TestSocialWarRoomTrigger:
    def test_seven_triggers(self):
        assert len(SocialWarRoomTrigger) == 7

    def test_trigger_values(self):
        values = {t.value for t in SocialWarRoomTrigger}
        assert "narrative_spike" in values
        assert "sentiment_crisis" in values
        assert "transfer_explosion" in values
        assert "breaking_story" in values
        assert "national_team_crisis" in values
        assert "referee_controversy" in values
        assert "media_attack" in values


class TestWarRoomPriority:
    def test_three_priorities(self):
        assert len(WarRoomPriority) == 3
        values = {p.value for p in WarRoomPriority}
        assert "P1" in values
        assert "P2" in values
        assert "P3" in values


class TestWarRoomStatus:
    def test_four_statuses(self):
        assert len(WarRoomStatus) == 4
        values = {s.value for s in WarRoomStatus}
        assert "active" in values
        assert "resolved" in values


class TestSocialWarRoomState:
    def test_creation(self):
        state = SocialWarRoomState(
            trigger=SocialWarRoomTrigger.BREAKING_STORY,
            priority=WarRoomPriority.P2,
        )
        assert state.war_room_id != ""
        assert state.trigger == SocialWarRoomTrigger.BREAKING_STORY
        assert state.status == WarRoomStatus.ACTIVE
        assert state.resolved_at is None

    def test_default_priority_p1(self):
        state = SocialWarRoomState(trigger=SocialWarRoomTrigger.SENTIMENT_CRISIS)
        assert state.priority == WarRoomPriority.P1


class TestSocialWarRoomReport:
    def test_creation(self):
        r = SocialWarRoomReport(
            trigger=SocialWarRoomTrigger.MEDIA_ATTACK,
            priority=WarRoomPriority.P1,
        )
        assert r.report_id != ""
        assert r.status == WarRoomStatus.ACTIVE

    def test_to_dict(self):
        r = SocialWarRoomReport(
            trigger=SocialWarRoomTrigger.NARRATIVE_SPIKE,
            priority=WarRoomPriority.P2,
            context_summary="Narrative spike detected.",
        )
        d = r.to_dict()
        assert d["trigger"] == "narrative_spike"
        assert d["priority"] == "P2"
        assert d["context_summary"] == "Narrative spike detected."

    def test_to_summary(self):
        r = SocialWarRoomReport(
            trigger=SocialWarRoomTrigger.TRANSFER_EXPLOSION,
            priority=WarRoomPriority.P1,
        )
        s = r.to_summary()
        assert "report_id" in s
        assert s["trigger"] == "transfer_explosion"
        assert s["priority"] == "P1"
        assert "activated_at" in s


class TestSocialWarRoomService:
    def test_singleton(self):
        assert get_war_room_service() is get_war_room_service()

    def test_init(self):
        service = SocialWarRoomService()
        assert service._active_rooms == {}

    @pytest.mark.asyncio
    async def test_activate_returns_state(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.BREAKING_STORY)
        assert isinstance(state, SocialWarRoomState)
        assert state.trigger == SocialWarRoomTrigger.BREAKING_STORY

    @pytest.mark.asyncio
    async def test_activate_assigns_personas(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.SENTIMENT_CRISIS)
        assert len(state.assigned_personas) > 0

    @pytest.mark.asyncio
    async def test_activate_p1_priority(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.SENTIMENT_CRISIS)
        assert state.priority == WarRoomPriority.P1

    @pytest.mark.asyncio
    async def test_activate_p3_priority(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.REFEREE_CONTROVERSY)
        assert state.priority == WarRoomPriority.P3

    @pytest.mark.asyncio
    async def test_activate_with_explicit_priority(self):
        service = SocialWarRoomService()
        state = await service.activate(
            SocialWarRoomTrigger.BREAKING_STORY,
            priority=WarRoomPriority.P1,
        )
        assert state.priority == WarRoomPriority.P1

    @pytest.mark.asyncio
    async def test_activate_with_context(self):
        service = SocialWarRoomService()
        state = await service.activate(
            SocialWarRoomTrigger.TRANSFER_EXPLOSION,
            context={"player": "Ronaldo", "fee": "100M"},
        )
        assert state.context["player"] == "Ronaldo"

    @pytest.mark.asyncio
    async def test_evaluate_sentiment_crisis_true(self):
        service = SocialWarRoomService()
        result = await service.evaluate(SocialWarRoomTrigger.SENTIMENT_CRISIS)
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_with_high_velocity_true(self):
        service = SocialWarRoomService()
        result = await service.evaluate(
            SocialWarRoomTrigger.BREAKING_STORY,
            context={"velocity": 8.0},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_low_velocity_false(self):
        service = SocialWarRoomService()
        result = await service.evaluate(
            SocialWarRoomTrigger.BREAKING_STORY,
            context={"velocity": 1.0},
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.BREAKING_STORY)
        report = await service.generate_report(state)
        assert isinstance(report, SocialWarRoomReport)

    @pytest.mark.asyncio
    async def test_report_has_responses(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.SENTIMENT_CRISIS)
        report = await service.generate_report(state)
        assert len(report.recommended_responses) > 0

    @pytest.mark.asyncio
    async def test_report_has_narrative_strategies(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.MEDIA_ATTACK)
        report = await service.generate_report(state)
        assert len(report.narrative_strategies) > 0

    @pytest.mark.asyncio
    async def test_report_has_executive_alerts(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.NATIONAL_TEAM_CRISIS)
        report = await service.generate_report(state)
        assert len(report.executive_alerts) > 0

    @pytest.mark.asyncio
    async def test_resolve_returns_true(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.BREAKING_STORY)
        result = await service.resolve(state.war_room_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_resolve_updates_status(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.BREAKING_STORY)
        await service.resolve(state.war_room_id)
        assert service._active_rooms[state.war_room_id].status == WarRoomStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_resolve_unknown_returns_false(self):
        service = SocialWarRoomService()
        result = await service.resolve("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_rooms(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.BREAKING_STORY)
        active = service.get_active_rooms()
        assert any(r["war_room_id"] == state.war_room_id for r in active)

    @pytest.mark.asyncio
    async def test_resolved_not_in_active(self):
        service = SocialWarRoomService()
        state = await service.activate(SocialWarRoomTrigger.BREAKING_STORY)
        await service.resolve(state.war_room_id)
        active = service.get_active_rooms()
        assert not any(r["war_room_id"] == state.war_room_id for r in active)
