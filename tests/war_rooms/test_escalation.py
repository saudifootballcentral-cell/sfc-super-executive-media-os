"""Tests for EscalationFramework."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.escalation.models import (
    EscalationLevel,
    EscalationRecord,
    EscalationTrigger,
)
from sfc.war_rooms.operations.escalation.service import EscalationFramework


class TestEscalationFramework:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = EscalationFramework()

    async def test_no_trigger_returns_none(self) -> None:
        result = await self.service.evaluate({"confidence_score": 90, "risk_score": 10})
        assert result is None

    async def test_low_confidence_triggers_l2(self) -> None:
        record = await self.service.evaluate({"confidence_score": 70})
        assert record is not None
        assert record.trigger == EscalationTrigger.LOW_CONFIDENCE
        assert record.level == EscalationLevel.L2_STRATEGIC

    async def test_high_risk_triggers_l3(self) -> None:
        record = await self.service.evaluate({"risk_score": 75})
        assert record is not None
        assert record.trigger == EscalationTrigger.HIGH_RISK
        assert record.level == EscalationLevel.L3_EXECUTIVE

    async def test_system_failure_triggers_l4(self) -> None:
        record = await self.service.evaluate({"system_failure": True})
        assert record is not None
        assert record.trigger == EscalationTrigger.SYSTEM_FAILURE
        assert record.level == EscalationLevel.L4_CRITICAL

    async def test_security_risk_triggers_l4(self) -> None:
        record = await self.service.evaluate({"security_risk": True})
        assert record is not None
        assert record.level == EscalationLevel.L4_CRITICAL

    async def test_brand_risk_triggers_l2(self) -> None:
        record = await self.service.evaluate({"brand_risk": True})
        assert record is not None
        assert record.trigger == EscalationTrigger.BRAND_RISK
        assert record.level == EscalationLevel.L2_STRATEGIC

    async def test_evaluate_publishes_event(self) -> None:
        await self.service.evaluate({"system_failure": True})
        history = get_event_bus().get_history("escalation_triggered")
        assert len(history) == 1

    async def test_resolve_marks_resolved(self) -> None:
        record = await self.service.evaluate({"confidence_score": 50})
        assert record is not None
        resolved = await self.service.resolve(record.escalation_id, "Issue addressed")
        assert resolved.resolved is True
        assert resolved.resolution == "Issue addressed"

    async def test_resolve_publishes_event(self) -> None:
        record = await self.service.evaluate({"confidence_score": 50})
        assert record is not None
        await self.service.resolve(record.escalation_id, "Fixed")
        history = get_event_bus().get_history("escalation_resolved")
        assert len(history) == 1

    async def test_get_open_escalations(self) -> None:
        await self.service.evaluate({"confidence_score": 50})
        await self.service.evaluate({"system_failure": True})
        open_esc = self.service.get_open_escalations()
        assert len(open_esc) == 2

    async def test_report_returns_report(self) -> None:
        await self.service.evaluate({"confidence_score": 50})
        report = await self.service.report("session")
        assert report.period == "session"
        assert report.total_escalations == 1

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "escalation_framework"
