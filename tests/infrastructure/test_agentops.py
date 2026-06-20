"""Tests for AgentOpsService."""

from __future__ import annotations

import pytest

from sfc.infrastructure.agentops.service import AgentOpsService
from sfc.infrastructure.shared.types import AuditEntry, ComponentHealth, HealthStatus


@pytest.fixture
def service() -> AgentOpsService:
    return AgentOpsService()


@pytest.mark.asyncio
async def test_initialize(service: AgentOpsService) -> None:
    """Service initializes without error."""
    await service.initialize()


def test_record_call_success(service: AgentOpsService) -> None:
    """record_call tracks successful calls."""
    service.record_call("test_component", success=True, latency_ms=100.0, cost_usd=0.01)

    report = service.health_report()
    assert "test_component" in report
    health = report["test_component"]
    assert health.status == HealthStatus.HEALTHY
    assert health.metrics["total_calls"] == 1


def test_record_call_failure(service: AgentOpsService) -> None:
    """record_call tracks failed calls and reflects in health score."""
    # Record many failures to drive down health score
    for _ in range(10):
        service.record_call("failing_component", success=False, latency_ms=500.0)

    report = service.health_report()
    assert "failing_component" in report
    # Health score should be 0 (all failed)
    score = report["failing_component"].metrics["health_score"]
    assert score == 0.0


def test_audit_creates_entry(service: AgentOpsService) -> None:
    """audit() appends to the audit registry."""
    entry = service.audit("editorial", "create_draft", "run-001", payload={"item": "test"})

    assert isinstance(entry, AuditEntry)
    assert entry.component == "editorial"
    assert entry.action == "create_draft"
    assert entry.run_id == "run-001"
    assert entry.payload == {"item": "test"}
    assert entry.success is True
    assert len(service.audit_registry) == 1


def test_audit_multiple_entries(service: AgentOpsService) -> None:
    """Multiple audit entries accumulate correctly."""
    service.audit("intelligence", "fetch_sources", "run-001")
    service.audit("editorial", "create_draft", "run-001")
    service.audit("governance", "review", "run-001", success=False)

    assert len(service.audit_registry) == 3
    assert service.audit_registry[2].success is False


def test_health_report_returns_component_health(service: AgentOpsService) -> None:
    """health_report() returns ComponentHealth objects."""
    service.record_call("comp_a", success=True, latency_ms=200.0)
    service.record_call("comp_b", success=True, latency_ms=300.0)

    report = service.health_report()
    for name, health in report.items():
        assert isinstance(health, ComponentHealth)
        assert isinstance(health.status, HealthStatus)


def test_health_report_empty_service(service: AgentOpsService) -> None:
    """health_report() works when no calls have been recorded."""
    report = service.health_report()
    # Should return at least one entry (agentops itself)
    assert len(report) >= 1


def test_cost_report(service: AgentOpsService) -> None:
    """cost_report() returns aggregated cost data."""
    service.record_call("claude", success=True, latency_ms=1500.0, cost_usd=0.05)
    service.record_call("claude", success=True, latency_ms=1200.0, cost_usd=0.03)

    report = service.cost_report()
    assert "total_cost_usd" in report
    assert report["total_cost_usd"] >= 0.08


def test_optimization_report_returns_list(service: AgentOpsService) -> None:
    """optimization_report() returns a non-empty list of strings."""
    report = service.optimization_report()
    assert isinstance(report, list)
    assert len(report) >= 1
    assert all(isinstance(s, str) for s in report)


def test_optimization_report_flags_high_cost(service: AgentOpsService) -> None:
    """optimization_report() flags when cost exceeds target."""
    # Simulate high cost
    for _ in range(10):
        service.record_call("expensive_llm", success=True, latency_ms=2000.0, cost_usd=0.05)

    report = service.optimization_report()
    # Should mention cost
    has_cost_mention = any("cost" in r.lower() or "$" in r for r in report)
    assert has_cost_mention


def test_health_check_returns_component_health(service: AgentOpsService) -> None:
    """health_check() returns ComponentHealth without raising."""
    health = service.health_check()
    assert isinstance(health, ComponentHealth)
    assert health.component == "agentops"
    assert health.status in list(HealthStatus)


def test_health_check_never_raises(service: AgentOpsService) -> None:
    """health_check() must never raise an exception."""
    # Even with a fresh service
    health = service.health_check()
    assert health is not None


def test_cost_recorded_in_monitor(service: AgentOpsService) -> None:
    """record_call with cost_usd updates the cost monitor."""
    service.record_call("claude", success=True, latency_ms=1000.0, cost_usd=0.05)
    cost_data = service.cost_report()
    assert cost_data["total_cost_usd"] > 0
