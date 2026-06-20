"""Tests for TransferWindowWarRoom."""

from __future__ import annotations

import pytest

from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomStatus, WarRoomType
from sfc.war_rooms.transfer_window.models import TransferItem, TransferStatus, TransferTracker
from sfc.war_rooms.transfer_window.service import TransferWindowWarRoom


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


@pytest.fixture
def war_room(registry: WarRoomRegistry) -> TransferWindowWarRoom:
    return TransferWindowWarRoom(registry)


class TestTransferWindowActivation:
    @pytest.mark.asyncio
    async def test_activate_creates_war_room_state(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        state = await war_room.activate()
        assert state is not None
        assert state.war_room_type == WarRoomType.TRANSFER_WINDOW

    @pytest.mark.asyncio
    async def test_activate_has_p3_priority(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        state = await war_room.activate()
        assert state.priority == WarRoomPriority.P3_MEDIUM

    @pytest.mark.asyncio
    async def test_activate_with_window_type(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        state = await war_room.activate(window_type="winter")
        assert state is not None
        assert war_room._tracker.window_type == "winter"

    @pytest.mark.asyncio
    async def test_activate_returns_existing_if_active(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        state1 = await war_room.activate()
        state2 = await war_room.activate()
        assert state1.war_room_id == state2.war_room_id


class TestTransferIngestion:
    @pytest.mark.asyncio
    async def test_ingest_transfer_returns_transfer_item(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Cristiano Ronaldo",
            "from_club": "Al Nassr",
            "to_club": "Manchester United",
            "sources": ["ESPN"],
        })
        assert isinstance(item, TransferItem)

    @pytest.mark.asyncio
    async def test_ingest_transfer_stores_player(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Karim Benzema",
            "from_club": "Al Ittihad",
            "to_club": "Real Madrid",
        })
        assert item.player == "Karim Benzema"

    @pytest.mark.asyncio
    async def test_ingest_transfer_updates_tracker(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        await war_room.ingest_transfer({
            "player": "Test Player",
            "from_club": "Club A",
            "to_club": "Club B",
        })
        assert war_room._tracker.total_tracked == 1

    @pytest.mark.asyncio
    async def test_ingest_saudi_related_flags_correctly(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Test Player",
            "from_club": "Al Hilal",
            "to_club": "Real Madrid",
        })
        assert item.is_saudi_related is True


class TestTransferClassification:
    @pytest.mark.asyncio
    async def test_one_source_returns_rumor(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
            "sources": ["Anonymous"],
        })
        assert status == TransferStatus.RUMOR

    @pytest.mark.asyncio
    async def test_no_sources_returns_rumor(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
        })
        assert status == TransferStatus.RUMOR

    @pytest.mark.asyncio
    async def test_two_sources_returns_strong_rumor(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
            "sources": ["Journalist A", "Journalist B"],
        })
        assert status == TransferStatus.STRONG_RUMOR

    @pytest.mark.asyncio
    async def test_official_announcement_returns_confirmation(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
            "official_announcement": True,
        })
        assert status == TransferStatus.OFFICIAL_CONFIRMATION

    @pytest.mark.asyncio
    async def test_player_confirmed_returns_verbal_agreement(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
            "player_confirmed": True,
        })
        assert status == TransferStatus.VERBAL_AGREEMENT

    @pytest.mark.asyncio
    async def test_club_source_with_fee_returns_advanced_negotiation(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
            "club_sources": True,
            "fee_estimate_m_eur": 50.0,
        })
        assert status == TransferStatus.ADVANCED_NEGOTIATION

    @pytest.mark.asyncio
    async def test_journalist_count_two_returns_strong_rumor(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        status = await war_room.classify_transfer({
            "player": "Test",
            "from_club": "A",
            "to_club": "B",
            "journalist_count": 2,
        })
        assert status == TransferStatus.STRONG_RUMOR


class TestTransferBrief:
    @pytest.mark.asyncio
    async def test_create_transfer_brief_returns_dict(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        brief = await war_room.create_transfer_brief()
        assert isinstance(brief, dict)

    @pytest.mark.asyncio
    async def test_create_transfer_brief_has_items_key(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        brief = await war_room.create_transfer_brief()
        assert "items" in brief

    @pytest.mark.asyncio
    async def test_brief_reflects_ingested_transfers(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        await war_room.ingest_transfer({"player": "P1", "from_club": "A", "to_club": "B"})
        await war_room.ingest_transfer({"player": "P2", "from_club": "C", "to_club": "D"})
        brief = await war_room.create_transfer_brief()
        assert brief["total_tracked"] == 2
        assert len(brief["items"]) == 2


class TestSquadImpact:
    @pytest.mark.asyncio
    async def test_analyze_squad_impact_returns_dict(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Test Player",
            "from_club": "Al Hilal",
            "to_club": "Real Madrid",
        })
        impact = await war_room.analyze_squad_impact(item)
        assert isinstance(impact, dict)

    @pytest.mark.asyncio
    async def test_analyze_squad_impact_has_required_keys(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Test Player",
            "from_club": "Al Hilal",
            "to_club": "Real Madrid",
        })
        impact = await war_room.analyze_squad_impact(item)
        assert "player" in impact
        assert "impact_assessment" in impact


class TestExecutiveAlert:
    @pytest.mark.asyncio
    async def test_create_executive_alert_returns_string(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Cristiano Ronaldo",
            "from_club": "Al Nassr",
            "to_club": "Man United",
            "official_announcement": True,
        })
        alert = await war_room.create_executive_alert(item)
        assert isinstance(alert, str)
        assert len(alert) > 0

    @pytest.mark.asyncio
    async def test_executive_alert_mentions_player(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        item = await war_room.ingest_transfer({
            "player": "Karim Benzema",
            "from_club": "Al Ittihad",
            "to_club": "Juventus",
        })
        alert = await war_room.create_executive_alert(item)
        assert "Karim Benzema" in alert


class TestTransferWindowHealthCheck:
    def test_health_check_never_raises(self, war_room: TransferWindowWarRoom) -> None:
        health = war_room.health_check()
        assert health is not None

    @pytest.mark.asyncio
    async def test_health_check_active_war_room(
        self, war_room: TransferWindowWarRoom
    ) -> None:
        await war_room.activate()
        health = war_room.health_check()
        assert health.status == "active"
