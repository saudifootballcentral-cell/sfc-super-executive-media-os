"""Tests for MatchDayWarRoom."""

from __future__ import annotations

import pytest

from sfc.war_rooms.match_day.models import MatchInfo, MatchPhase
from sfc.war_rooms.match_day.service import MatchDayWarRoom
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomHealth, WarRoomPriority, WarRoomStatus, WarRoomType


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


@pytest.fixture
def war_room(registry: WarRoomRegistry) -> MatchDayWarRoom:
    return MatchDayWarRoom(registry)


@pytest.fixture
def match_info() -> MatchInfo:
    return MatchInfo(
        home_team="Al Hilal",
        away_team="Al Nassr",
        competition="Saudi Pro League",
        venue="King Fahd Stadium",
    )


class TestMatchDayActivation:
    @pytest.mark.asyncio
    async def test_activate_creates_war_room_state(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        state = await war_room.activate(match_info)
        assert state is not None
        assert state.war_room_type == WarRoomType.MATCH_DAY

    @pytest.mark.asyncio
    async def test_activate_creates_active_status(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        state = await war_room.activate(match_info)
        assert state.status == WarRoomStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_has_p3_priority(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        state = await war_room.activate(match_info)
        assert state.priority == WarRoomPriority.P3_MEDIUM

    @pytest.mark.asyncio
    async def test_activate_returns_existing_if_already_active(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo, registry: WarRoomRegistry
    ) -> None:
        state1 = await war_room.activate(match_info)
        state2 = await war_room.activate(match_info)
        assert state1.war_room_id == state2.war_room_id


class TestMatchBrief:
    @pytest.mark.asyncio
    async def test_create_match_brief_returns_dict(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        brief = await war_room.create_match_brief(match_info)
        assert isinstance(brief, dict)

    @pytest.mark.asyncio
    async def test_create_match_brief_has_home_team(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        brief = await war_room.create_match_brief(match_info)
        assert brief["home_team"] == "Al Hilal"

    @pytest.mark.asyncio
    async def test_create_match_brief_has_away_team(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        brief = await war_room.create_match_brief(match_info)
        assert brief["away_team"] == "Al Nassr"

    @pytest.mark.asyncio
    async def test_create_match_brief_has_competition(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        brief = await war_room.create_match_brief(match_info)
        assert brief["competition"] == "Saudi Pro League"

    @pytest.mark.asyncio
    async def test_create_match_brief_has_tactical_preview(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        brief = await war_room.create_match_brief(match_info)
        assert "tactical_preview" in brief

    @pytest.mark.asyncio
    async def test_create_match_brief_has_lineup_analysis(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        brief = await war_room.create_match_brief(match_info)
        assert "lineup_analysis" in brief


class TestContentPlan:
    @pytest.mark.asyncio
    async def test_create_content_plan_returns_list(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        plan = await war_room.create_content_plan(match_info, MatchPhase.PRE_MATCH)
        assert isinstance(plan, list)

    @pytest.mark.asyncio
    async def test_pre_match_content_plan_not_empty(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        plan = await war_room.create_content_plan(match_info, MatchPhase.PRE_MATCH)
        assert len(plan) > 0

    @pytest.mark.asyncio
    async def test_live_content_plan_not_empty(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        plan = await war_room.create_content_plan(match_info, MatchPhase.LIVE)
        assert len(plan) > 0

    @pytest.mark.asyncio
    async def test_post_match_content_plan_not_empty(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        plan = await war_room.create_content_plan(match_info, MatchPhase.POST_MATCH)
        assert len(plan) > 0

    @pytest.mark.asyncio
    async def test_content_plan_items_have_type(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        plan = await war_room.create_content_plan(match_info, MatchPhase.PRE_MATCH)
        for item in plan:
            assert "type" in item


class TestPlayerRatings:
    @pytest.mark.asyncio
    async def test_create_player_ratings_returns_list(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        ratings = await war_room.create_player_ratings(match_info, {})
        assert isinstance(ratings, list)

    @pytest.mark.asyncio
    async def test_player_ratings_not_empty(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        ratings = await war_room.create_player_ratings(match_info, {})
        assert len(ratings) > 0

    @pytest.mark.asyncio
    async def test_player_ratings_have_player_field(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        ratings = await war_room.create_player_ratings(match_info, {})
        for r in ratings:
            assert "player" in r

    @pytest.mark.asyncio
    async def test_player_ratings_have_rating_field(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        ratings = await war_room.create_player_ratings(match_info, {})
        for r in ratings:
            assert "rating" in r

    @pytest.mark.asyncio
    async def test_player_ratings_have_rationale_field(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        ratings = await war_room.create_player_ratings(match_info, {})
        for r in ratings:
            assert "rationale" in r

    @pytest.mark.asyncio
    async def test_custom_player_data_used(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        performance_data = {
            "players": [
                {"name": "Cristiano Ronaldo", "team": "Al Nassr", "rating": 9.0, "rationale": "Hat-trick"},
                {"name": "Neymar Jr", "team": "Al Hilal", "rating": 7.5, "rationale": "Good performance"},
            ]
        }
        ratings = await war_room.create_player_ratings(match_info, performance_data)
        names = [r["player"] for r in ratings]
        assert "Cristiano Ronaldo" in names


class TestExecutiveSummary:
    @pytest.mark.asyncio
    async def test_executive_summary_returns_non_empty_string(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        await war_room.activate(match_info)
        summary = await war_room.create_executive_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_executive_summary_mentions_teams(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        await war_room.activate(match_info)
        summary = await war_room.create_executive_summary()
        assert "Al Hilal" in summary or "Al Nassr" in summary


class TestMatchDayHealthCheck:
    def test_health_check_never_raises(
        self, war_room: MatchDayWarRoom
    ) -> None:
        health = war_room.health_check()
        assert health is not None
        assert "war_room_id" in WarRoomHealth.model_fields

    @pytest.mark.asyncio
    async def test_health_check_active_war_room(
        self, war_room: MatchDayWarRoom, match_info: MatchInfo
    ) -> None:
        await war_room.activate(match_info)
        health = war_room.health_check()
        assert health.status == "active"
        assert health.health_score >= 0
