"""Tests for CrisisWarRoom."""

from __future__ import annotations

import pytest

from sfc.war_rooms.crisis.models import CrisisEvent, CrisisReport, CrisisSeverity, CrisisType
from sfc.war_rooms.crisis.service import CrisisWarRoom
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomStatus, WarRoomType


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


@pytest.fixture
def war_room(registry: WarRoomRegistry) -> CrisisWarRoom:
    return CrisisWarRoom(registry)


@pytest.fixture
def crisis_event() -> CrisisEvent:
    return CrisisEvent(
        crisis_type=CrisisType.FAKE_NEWS,
        severity=CrisisSeverity.HIGH,
        description="False transfer rumor spreading virally.",
        affected_platforms=["x", "instagram"],
    )


@pytest.fixture
def critical_crisis() -> CrisisEvent:
    return CrisisEvent(
        crisis_type=CrisisType.PUBLISHING_ERROR,
        severity=CrisisSeverity.CRITICAL,
        description="Incorrect match score published.",
        affected_content_ids=["content-001"],
        affected_platforms=["x"],
    )


class TestCrisisWarRoomActivation:
    @pytest.mark.asyncio
    async def test_activate_creates_p1_critical_state(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        state = await war_room.activate(crisis_event)
        assert state.priority == WarRoomPriority.P1_CRITICAL

    @pytest.mark.asyncio
    async def test_activate_creates_active_status(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        state = await war_room.activate(crisis_event)
        assert state.status == WarRoomStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_sets_crisis_type(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        state = await war_room.activate(crisis_event)
        assert state.war_room_type == WarRoomType.CRISIS

    @pytest.mark.asyncio
    async def test_activate_adds_crisis_to_active_list(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        await war_room.activate(crisis_event)
        assert len(war_room.get_active_crises()) == 1

    @pytest.mark.asyncio
    async def test_activate_second_crisis_updates_existing(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent, critical_crisis: CrisisEvent
    ) -> None:
        state1 = await war_room.activate(crisis_event)
        state2 = await war_room.activate(critical_crisis)
        # Same war room instance used
        assert state1.war_room_id == state2.war_room_id
        assert len(war_room.get_active_crises()) == 2


class TestCrisisAssessment:
    @pytest.mark.asyncio
    async def test_assess_crisis_returns_crisis_report(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = await war_room.assess_crisis(crisis_event)
        assert isinstance(report, CrisisReport)

    @pytest.mark.asyncio
    async def test_assess_crisis_report_has_crisis_id(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = await war_room.assess_crisis(crisis_event)
        assert report.crisis_id == crisis_event.crisis_id

    @pytest.mark.asyncio
    async def test_assess_crisis_has_containment_actions(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = await war_room.assess_crisis(crisis_event)
        assert len(report.containment_actions) > 0

    @pytest.mark.asyncio
    async def test_assess_crisis_has_damage_assessment(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = await war_room.assess_crisis(crisis_event)
        assert isinstance(report.damage_assessment, dict)

    @pytest.mark.asyncio
    async def test_assess_crisis_has_recovery_plan(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = await war_room.assess_crisis(crisis_event)
        assert len(report.recovery_plan) > 0

    @pytest.mark.asyncio
    async def test_assess_crisis_has_executive_alert(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = await war_room.assess_crisis(crisis_event)
        assert isinstance(report.executive_alert, str)
        assert len(report.executive_alert) > 0


class TestCrisisVerification:
    @pytest.mark.asyncio
    async def test_verify_crisis_returns_dict(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        result = await war_room.verify_crisis(crisis_event)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_verify_crisis_has_verified_field(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        result = await war_room.verify_crisis(crisis_event)
        assert "verified" in result

    @pytest.mark.asyncio
    async def test_verify_crisis_has_assessment_field(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        result = await war_room.verify_crisis(crisis_event)
        assert "assessment" in result


class TestContainmentPlan:
    @pytest.mark.asyncio
    async def test_containment_plan_returns_non_empty_list(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        report = CrisisReport(
            crisis_id=crisis_event.crisis_id,
            crisis_type=crisis_event.crisis_type,
            severity=crisis_event.severity,
            description=crisis_event.description,
            detected_at=crisis_event.detected_at,
        )
        plan = await war_room.create_containment_plan(report)
        assert isinstance(plan, list)
        assert len(plan) > 0

    @pytest.mark.asyncio
    async def test_fake_news_containment_specific_actions(
        self, war_room: CrisisWarRoom
    ) -> None:
        fake_news_crisis = CrisisEvent(
            crisis_type=CrisisType.FAKE_NEWS,
            severity=CrisisSeverity.HIGH,
            description="Fake news detected.",
        )
        report = CrisisReport(
            crisis_id=fake_news_crisis.crisis_id,
            crisis_type=fake_news_crisis.crisis_type,
            severity=fake_news_crisis.severity,
            description=fake_news_crisis.description,
            detected_at=fake_news_crisis.detected_at,
        )
        plan = await war_room.create_containment_plan(report)
        assert len(plan) > 0
        # Should mention correction
        plan_text = " ".join(plan)
        assert "correction" in plan_text.lower()

    @pytest.mark.asyncio
    async def test_platform_strike_containment_mentions_appeal(
        self, war_room: CrisisWarRoom
    ) -> None:
        strike_crisis = CrisisEvent(
            crisis_type=CrisisType.PLATFORM_STRIKE,
            severity=CrisisSeverity.HIGH,
            description="Platform strike received.",
        )
        report = CrisisReport(
            crisis_id=strike_crisis.crisis_id,
            crisis_type=strike_crisis.crisis_type,
            severity=strike_crisis.severity,
            description=strike_crisis.description,
            detected_at=strike_crisis.detected_at,
        )
        plan = await war_room.create_containment_plan(report)
        plan_text = " ".join(plan)
        assert "appeal" in plan_text.lower()


class TestExecutiveAlert:
    @pytest.mark.asyncio
    async def test_create_executive_alert_returns_non_empty_string(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        alert = await war_room.create_executive_alert(crisis_event)
        assert isinstance(alert, str)
        assert len(alert) > 0

    @pytest.mark.asyncio
    async def test_executive_alert_mentions_severity(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        alert = await war_room.create_executive_alert(crisis_event)
        assert "HIGH" in alert.upper()

    @pytest.mark.asyncio
    async def test_executive_alert_mentions_crisis_type(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        alert = await war_room.create_executive_alert(crisis_event)
        # FAKE_NEWS becomes "Fake News" in title case
        assert "Fake" in alert or "fake_news" in alert.lower() or "FAKE" in alert


class TestCrisisResolution:
    @pytest.mark.asyncio
    async def test_resolve_crisis_marks_status_resolved(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        await war_room.activate(crisis_event)
        await war_room.assess_crisis(crisis_event)
        report = await war_room.resolve_crisis(crisis_event.crisis_id, "Issue contained")
        assert report.status == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_crisis_sets_resolved_at(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        await war_room.activate(crisis_event)
        await war_room.assess_crisis(crisis_event)
        report = await war_room.resolve_crisis(crisis_event.crisis_id)
        assert report.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_crisis_includes_resolution_notes(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        await war_room.activate(crisis_event)
        await war_room.assess_crisis(crisis_event)
        report = await war_room.resolve_crisis(crisis_event.crisis_id, "Correction published")
        assert any("Correction published" in lesson for lesson in report.lessons_learned)

    @pytest.mark.asyncio
    async def test_resolve_unknown_crisis_raises(
        self, war_room: CrisisWarRoom
    ) -> None:
        with pytest.raises(ValueError):
            await war_room.resolve_crisis("CRS-UNKNOWN-0000")


class TestCrisisHealthCheck:
    def test_health_check_never_raises(self, war_room: CrisisWarRoom) -> None:
        health = war_room.health_check()
        assert health is not None

    @pytest.mark.asyncio
    async def test_health_check_active_war_room(
        self, war_room: CrisisWarRoom, crisis_event: CrisisEvent
    ) -> None:
        await war_room.activate(crisis_event)
        health = war_room.health_check()
        assert health.status == "active"
