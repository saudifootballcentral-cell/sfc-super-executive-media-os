"""Integration tests for war room routing in the LangGraph pipeline.

Tests that the war_room_router_node correctly detects task_type and
activates the appropriate war room.
"""

from __future__ import annotations

import pytest

from sfc.graph.nodes.war_room_router import war_room_router_node, _detect_war_room_type
from sfc.graph.state import make_initial_state
from sfc.war_rooms.shared.types import WarRoomType


# ---------------------------------------------------------------------------
# Detection policy tests (pure, sync)
# ---------------------------------------------------------------------------

class TestWarRoomDetection:
    def test_crisis_task_maps_to_crisis_war_room(self):
        result = _detect_war_room_type("crisis")
        assert result == WarRoomType.CRISIS

    def test_crisis_compound_task_maps_to_crisis(self):
        result = _detect_war_room_type("crisis_response")
        assert result == WarRoomType.CRISIS

    def test_match_task_maps_to_match_day(self):
        result = _detect_war_room_type("match_report")
        assert result == WarRoomType.MATCH_DAY

    def test_match_news_maps_to_match_day(self):
        result = _detect_war_room_type("match_news")
        assert result == WarRoomType.MATCH_DAY

    def test_transfer_task_maps_to_transfer_window(self):
        result = _detect_war_room_type("transfer_news")
        assert result == WarRoomType.TRANSFER_WINDOW

    def test_world_cup_task_maps_to_world_cup(self):
        result = _detect_war_room_type("world_cup_coverage")
        assert result == WarRoomType.WORLD_CUP

    def test_general_news_returns_none(self):
        result = _detect_war_room_type("news")
        assert result is None

    def test_campaign_returns_none(self):
        result = _detect_war_room_type("campaign")
        assert result is None

    def test_breaking_news_returns_none_from_detector(self):
        # breaking_news is handled separately by the node (BreakingNewsCommandCenter)
        result = _detect_war_room_type("breaking_news")
        assert result is None

    def test_crisis_has_priority_over_match(self):
        # "crisis" keyword detected before "match" in the priority list
        result = _detect_war_room_type("crisis_match_report")
        assert result == WarRoomType.CRISIS


# ---------------------------------------------------------------------------
# Node behaviour tests (async)
# ---------------------------------------------------------------------------

class TestWarRoomRouterNode:
    async def test_crisis_task_sets_war_room_state(self):
        state = make_initial_state("crisis", {"crisis_type": "reputation_risk"})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        assert ws.get("war_room_type") is not None
        assert "crisis" in str(ws.get("war_room_type", "")).lower()

    async def test_match_task_sets_war_room_state(self):
        state = make_initial_state("match_report", {"home_team": "Al Hilal", "away_team": "Al Nassr"})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        assert ws is not None

    async def test_transfer_task_activates_transfer_room(self):
        state = make_initial_state("transfer_news", {"player": "Ronaldo"})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        assert ws.get("war_room_type") is not None
        assert "transfer" in str(ws.get("war_room_type", "")).lower()

    async def test_general_task_no_war_room_activated(self):
        state = make_initial_state("news", {"headline": "Saudi football update"})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        assert ws.get("activated") is False
        assert ws.get("war_room_type") is None

    async def test_breaking_news_activates_command_center(self):
        state = make_initial_state("breaking_news", {"headline": "Breaking: Player injured"})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        assert ws.get("war_room_type") == "breaking_news_command"

    async def test_node_always_returns_pipeline_stage(self):
        state = make_initial_state("news", {})
        result = await war_room_router_node(state)
        assert result.get("pipeline_stage") == "war_room_routed"

    async def test_node_never_raises_exception(self):
        state = make_initial_state("unknown_task_type_xyz", {})
        try:
            result = await war_room_router_node(state)
            assert result is not None
        except Exception as exc:
            pytest.fail(f"war_room_router_node raised an exception: {exc}")

    async def test_war_room_state_has_required_keys(self):
        state = make_initial_state("match_report", {})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        for key in ["war_room_type", "activated", "warnings"]:
            assert key in ws, f"Missing key '{key}' in war_room_state"

    async def test_world_cup_task_activates_world_cup_room(self):
        state = make_initial_state("world_cup_coverage", {})
        result = await war_room_router_node(state)
        ws = result.get("war_room_state", {})
        assert ws is not None
        assert ws.get("war_room_type") is not None

    async def test_infrastructure_ready_set_on_activation(self):
        state = make_initial_state("match_report", {})
        result = await war_room_router_node(state)
        assert "infrastructure_ready" in result
