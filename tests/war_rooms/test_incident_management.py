"""Tests for IncidentManagementEngine."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.incident_management.models import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    Postmortem,
    RecoveryPlan,
)
from sfc.war_rooms.operations.incident_management.service import IncidentManagementEngine


class TestIncidentManagementEngine:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = IncidentManagementEngine()

    async def test_detect_creates_incident(self) -> None:
        incident = await self.service.detect(
            incident_type=IncidentType.PLATFORM_FAILURE,
            severity=IncidentSeverity.P3,
            title="Twitter API down",
            description="Twitter API returning 503",
            impact="Social publishing halted",
            affected_components=["twitter_publisher"],
        )
        assert isinstance(incident, Incident)
        assert incident.incident_id.startswith("INC-")
        assert incident.status == IncidentStatus.DETECTED

    async def test_detect_publishes_event(self) -> None:
        await self.service.detect(
            incident_type=IncidentType.AGENT_FAILURE,
            severity=IncidentSeverity.P2,
            title="Editorial agent down",
            description="Agent crashed",
            impact="Content creation halted",
            affected_components=["editorial_agent"],
        )
        history = get_event_bus().get_history("incident_detected")
        assert len(history) == 1

    async def test_p1_incident_raises_executive_alert(self) -> None:
        get_event_bus().reset()
        await self.service.detect(
            incident_type=IncidentType.SECURITY_INCIDENT,
            severity=IncidentSeverity.P1,
            title="Security breach",
            description="Unauthorized access detected",
            impact="Data at risk",
            affected_components=["auth_service"],
        )
        # Executive alert should also be triggered
        exec_alerts = get_event_bus().get_history("executive_alert_triggered")
        assert len(exec_alerts) >= 1

    async def test_contain_updates_status(self) -> None:
        incident = await self.service.detect(
            incident_type=IncidentType.TOOL_FAILURE,
            severity=IncidentSeverity.P3,
            title="Tool down",
            description="Tool broken",
            impact="Minor",
            affected_components=["tool_x"],
        )
        contained = await self.service.contain(incident.incident_id, "Isolated the failing tool")
        assert contained.status == IncidentStatus.CONTAINED
        assert contained.contained_at is not None

    async def test_recover_generates_plan(self) -> None:
        incident = await self.service.detect(
            incident_type=IncidentType.PUBLISHING_FAILURE,
            severity=IncidentSeverity.P2,
            title="Publishing down",
            description="Queue stuck",
            impact="No content published",
            affected_components=["publishing_queue"],
        )
        plan = await self.service.recover(incident.incident_id)
        assert isinstance(plan, RecoveryPlan)
        assert len(plan.steps) > 0
        assert plan.incident_id == incident.incident_id

    async def test_resolve_publishes_event(self) -> None:
        incident = await self.service.detect(
            incident_type=IncidentType.DATA_FAILURE,
            severity=IncidentSeverity.P3,
            title="Data corrupted",
            description="DB corruption",
            impact="Analytics unavailable",
            affected_components=["analytics_db"],
        )
        get_event_bus().reset()
        await self.service.resolve(incident.incident_id, "Restored from backup")
        history = get_event_bus().get_history("incident_resolved")
        assert len(history) == 1

    async def test_resolve_sets_root_cause(self) -> None:
        incident = await self.service.detect(
            incident_type=IncidentType.GOVERNANCE_FAILURE,
            severity=IncidentSeverity.P4,
            title="Policy breach",
            description="Content policy violated",
            impact="Reputational risk",
            affected_components=["governance_engine"],
        )
        resolved = await self.service.resolve(incident.incident_id, "Policy updated")
        assert resolved.root_cause == "Policy updated"

    async def test_create_postmortem(self) -> None:
        incident = await self.service.detect(
            incident_type=IncidentType.PLATFORM_FAILURE,
            severity=IncidentSeverity.P2,
            title="Platform outage",
            description="Full outage",
            impact="All publishing halted",
            affected_components=["website"],
        )
        await self.service.resolve(incident.incident_id, "Fixed network issue")
        postmortem = await self.service.create_postmortem(incident.incident_id)
        assert isinstance(postmortem, Postmortem)
        assert postmortem.incident_id == incident.incident_id
        assert len(postmortem.action_items) > 0

    async def test_get_open_incidents(self) -> None:
        inc = await self.service.detect(
            incident_type=IncidentType.TOOL_FAILURE,
            severity=IncidentSeverity.P4,
            title="Tool minor",
            description="Minor",
            impact="Minimal",
            affected_components=["tool_a"],
        )
        open_incs = self.service.get_open_incidents()
        assert inc.incident_id in [i.incident_id for i in open_incs]

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "incident_management_engine"
