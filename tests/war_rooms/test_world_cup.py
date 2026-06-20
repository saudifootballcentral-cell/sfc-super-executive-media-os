"""Tests for WorldCupWarRoom."""

from __future__ import annotations

import pytest

from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomStatus, WarRoomType
from sfc.war_rooms.world_cup.models import NationalTeamMonitor, WorldCupBrief, WorldCupPhase
from sfc.war_rooms.world_cup.service import WorldCupWarRoom


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


@pytest.fixture
def war_room(registry: WarRoomRegistry) -> WorldCupWarRoom:
    return WorldCupWarRoom(registry)


class TestWorldCupActivation:
    @pytest.mark.asyncio
    async def test_activate_creates_p1_critical_state(
        self, war_room: WorldCupWarRoom
    ) -> None:
        state = await war_room.activate()
        assert state.priority == WarRoomPriority.P1_CRITICAL

    @pytest.mark.asyncio
    async def test_activate_creates_active_status(
        self, war_room: WorldCupWarRoom
    ) -> None:
        state = await war_room.activate()
        assert state.status == WarRoomStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_world_cup_type(
        self, war_room: WorldCupWarRoom
    ) -> None:
        state = await war_room.activate()
        assert state.war_room_type == WarRoomType.WORLD_CUP

    @pytest.mark.asyncio
    async def test_activate_returns_existing_if_already_active(
        self, war_room: WorldCupWarRoom
    ) -> None:
        state1 = await war_room.activate()
        state2 = await war_room.activate()
        assert state1.war_room_id == state2.war_room_id

    @pytest.mark.asyncio
    async def test_activate_with_metadata(
        self, war_room: WorldCupWarRoom
    ) -> None:
        state = await war_room.activate(tournament_metadata={"edition": "2026"})
        assert state is not None


class TestDailyBrief:
    @pytest.mark.asyncio
    async def test_create_daily_brief_returns_world_cup_brief(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = await war_room.create_daily_brief(WorldCupPhase.PRE_TOURNAMENT, team_monitor)
        assert isinstance(brief, WorldCupBrief)

    @pytest.mark.asyncio
    async def test_create_daily_brief_has_correct_phase(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = await war_room.create_daily_brief(WorldCupPhase.GROUP_STAGE, team_monitor)
        assert brief.phase == WorldCupPhase.GROUP_STAGE

    @pytest.mark.asyncio
    async def test_create_daily_brief_has_national_team(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor(team="Saudi Arabia")
        brief = await war_room.create_daily_brief(WorldCupPhase.KNOCKOUT, team_monitor)
        assert brief.national_team.team == "Saudi Arabia"

    @pytest.mark.asyncio
    async def test_create_daily_brief_has_narrative_opportunities(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = await war_room.create_daily_brief(WorldCupPhase.PRE_TOURNAMENT, team_monitor)
        assert isinstance(brief.narrative_opportunities, list)
        assert len(brief.narrative_opportunities) > 0

    @pytest.mark.asyncio
    async def test_create_daily_brief_has_content_plan(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = await war_room.create_daily_brief(WorldCupPhase.GROUP_STAGE, team_monitor)
        assert isinstance(brief.daily_content_plan, list)
        assert len(brief.daily_content_plan) > 0

    @pytest.mark.asyncio
    async def test_create_daily_brief_has_executive_report(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = await war_room.create_daily_brief(WorldCupPhase.FINAL_WEEK, team_monitor)
        assert isinstance(brief.executive_report, str)
        assert len(brief.executive_report) > 0


class TestNationalTeamMonitoring:
    @pytest.mark.asyncio
    async def test_monitor_national_team_returns_monitor(
        self, war_room: WorldCupWarRoom
    ) -> None:
        monitor = await war_room.monitor_national_team()
        assert isinstance(monitor, NationalTeamMonitor)

    @pytest.mark.asyncio
    async def test_monitor_national_team_default_team(
        self, war_room: WorldCupWarRoom
    ) -> None:
        monitor = await war_room.monitor_national_team()
        assert monitor.team == "Saudi Arabia"

    @pytest.mark.asyncio
    async def test_monitor_national_team_updates_results(
        self, war_room: WorldCupWarRoom
    ) -> None:
        match_data = {"result": "Saudi Arabia 1-0 Opponent"}
        monitor = await war_room.monitor_national_team(match_data)
        assert len(monitor.results) > 0

    @pytest.mark.asyncio
    async def test_monitor_national_team_has_narratives(
        self, war_room: WorldCupWarRoom
    ) -> None:
        monitor = await war_room.monitor_national_team()
        assert isinstance(monitor.key_narratives, list)
        assert len(monitor.key_narratives) > 0


class TestOpponentReport:
    @pytest.mark.asyncio
    async def test_create_opponent_report_returns_dict(
        self, war_room: WorldCupWarRoom
    ) -> None:
        report = await war_room.create_opponent_report("Argentina")
        assert isinstance(report, dict)

    @pytest.mark.asyncio
    async def test_create_opponent_report_has_opponent_key(
        self, war_room: WorldCupWarRoom
    ) -> None:
        report = await war_room.create_opponent_report("Brazil")
        assert "opponent" in report
        assert report["opponent"] == "Brazil"

    @pytest.mark.asyncio
    async def test_create_opponent_report_has_historical_record(
        self, war_room: WorldCupWarRoom
    ) -> None:
        report = await war_room.create_opponent_report("Argentina")
        assert "historical_record_vs_saudi" in report


class TestNarrativeOpportunities:
    @pytest.mark.asyncio
    async def test_detect_narrative_opportunities_returns_list(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = WorldCupBrief(phase=WorldCupPhase.PRE_TOURNAMENT, national_team=team_monitor)
        opportunities = await war_room.detect_narrative_opportunities(brief)
        assert isinstance(opportunities, list)

    @pytest.mark.asyncio
    async def test_detect_narrative_opportunities_not_empty(
        self, war_room: WorldCupWarRoom
    ) -> None:
        team_monitor = NationalTeamMonitor()
        brief = WorldCupBrief(phase=WorldCupPhase.GROUP_STAGE, national_team=team_monitor)
        opportunities = await war_room.detect_narrative_opportunities(brief)
        assert len(opportunities) > 0


class TestSponsorActivations:
    @pytest.mark.asyncio
    async def test_create_sponsor_activations_returns_list(
        self, war_room: WorldCupWarRoom
    ) -> None:
        activations = await war_room.create_sponsor_activations(WorldCupPhase.PRE_TOURNAMENT)
        assert isinstance(activations, list)

    @pytest.mark.asyncio
    async def test_sponsor_activations_not_empty(
        self, war_room: WorldCupWarRoom
    ) -> None:
        activations = await war_room.create_sponsor_activations(WorldCupPhase.GROUP_STAGE)
        assert len(activations) > 0


class TestWorldCupHealthCheck:
    def test_health_check_never_raises(self, war_room: WorldCupWarRoom) -> None:
        health = war_room.health_check()
        assert health is not None

    @pytest.mark.asyncio
    async def test_health_check_active_war_room(
        self, war_room: WorldCupWarRoom
    ) -> None:
        await war_room.activate()
        health = war_room.health_check()
        assert health.status == "active"
        assert health.health_score >= 0
