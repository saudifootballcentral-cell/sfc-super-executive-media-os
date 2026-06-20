"""Tests for ActivationEngine."""

from __future__ import annotations

import pytest

from sfc.war_rooms.activation.models import ActivationRequest, ActivationTrigger
from sfc.war_rooms.activation.service import ActivationEngine
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomType


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


@pytest.fixture
def engine(registry: WarRoomRegistry) -> ActivationEngine:
    return ActivationEngine(registry)


class TestActivationEngineBasic:
    @pytest.mark.asyncio
    async def test_activate_returns_success_result(
        self, engine: ActivationEngine
    ) -> None:
        request = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        result = await engine.activate(request)
        assert result.success is True
        assert result.war_room_id is not None
        assert result.war_room_state is not None
        assert result.activated_at is not None

    @pytest.mark.asyncio
    async def test_activate_crisis(self, engine: ActivationEngine) -> None:
        request = ActivationRequest(
            war_room_type=WarRoomType.CRISIS,
            trigger=ActivationTrigger.CRISIS_DETECTED,
        )
        result = await engine.activate(request)
        assert result.success is True
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.CRISIS

    @pytest.mark.asyncio
    async def test_activate_world_cup(self, engine: ActivationEngine) -> None:
        request = ActivationRequest(
            war_room_type=WarRoomType.WORLD_CUP,
            trigger=ActivationTrigger.WORLD_CUP_MODE,
        )
        result = await engine.activate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_activate_transfer_window(self, engine: ActivationEngine) -> None:
        request = ActivationRequest(
            war_room_type=WarRoomType.TRANSFER_WINDOW,
            trigger=ActivationTrigger.TRANSFER_WINDOW_OPEN,
        )
        result = await engine.activate(request)
        assert result.success is True


class TestActivationEngineDuplicateHandling:
    @pytest.mark.asyncio
    async def test_duplicate_activation_blocked(self, engine: ActivationEngine) -> None:
        """Second activation of same type without force returns failure."""
        request = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        await engine.activate(request)
        result2 = await engine.activate(request)
        assert result2.success is False
        assert len(result2.reasons) > 0

    @pytest.mark.asyncio
    async def test_duplicate_activation_returns_existing_id(
        self, engine: ActivationEngine
    ) -> None:
        request = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        result1 = await engine.activate(request)
        result2 = await engine.activate(request)
        assert result2.war_room_id == result1.war_room_id

    @pytest.mark.asyncio
    async def test_force_true_bypasses_duplicate_check(
        self, engine: ActivationEngine
    ) -> None:
        """force=True deactivates existing and activates fresh."""
        request = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        result1 = await engine.activate(request)

        force_request = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.EXECUTIVE_ACTIVATION,
            force=True,
        )
        result2 = await engine.activate(force_request)
        assert result2.success is True
        assert result2.war_room_id != result1.war_room_id


class TestActivationEngineEventMapping:
    @pytest.mark.asyncio
    async def test_crisis_detected_maps_to_crisis(self, engine: ActivationEngine) -> None:
        result = await engine.activate_by_event("crisis_detected")
        assert result is not None
        assert result.success is True
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.CRISIS

    @pytest.mark.asyncio
    async def test_match_triggered_maps_to_match_day(
        self, engine: ActivationEngine
    ) -> None:
        result = await engine.activate_by_event("match_triggered")
        assert result is not None
        assert result.success is True
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.MATCH_DAY

    @pytest.mark.asyncio
    async def test_world_cup_triggered_maps_to_world_cup(
        self, engine: ActivationEngine
    ) -> None:
        result = await engine.activate_by_event("world_cup_triggered")
        assert result is not None
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.WORLD_CUP

    @pytest.mark.asyncio
    async def test_transfer_window_triggered_maps_to_transfer_window(
        self, engine: ActivationEngine
    ) -> None:
        result = await engine.activate_by_event("transfer_window_triggered")
        assert result is not None
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.TRANSFER_WINDOW

    @pytest.mark.asyncio
    async def test_unknown_event_returns_none(self, engine: ActivationEngine) -> None:
        result = await engine.activate_by_event("totally_unknown_event")
        assert result is None

    @pytest.mark.asyncio
    async def test_activate_by_event_with_metadata(
        self, engine: ActivationEngine
    ) -> None:
        result = await engine.activate_by_event(
            "crisis_detected", metadata={"description": "Test crisis"}
        )
        assert result is not None
        assert result.success is True


class TestActivationEngineWarnings:
    @pytest.mark.asyncio
    async def test_conflict_warning_when_incompatible(
        self, engine: ActivationEngine, registry: WarRoomRegistry
    ) -> None:
        """Activating two of the same type warns about conflict (first goes through)."""
        request1 = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        await engine.activate(request1)

        # Second same type should fail, not just warn
        request2 = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        result = await engine.activate(request2)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_activation_result_has_activated_at(
        self, engine: ActivationEngine
    ) -> None:
        request = ActivationRequest(
            war_room_type=WarRoomType.CRISIS,
            trigger=ActivationTrigger.CRISIS_DETECTED,
        )
        result = await engine.activate(request)
        assert result.activated_at is not None
