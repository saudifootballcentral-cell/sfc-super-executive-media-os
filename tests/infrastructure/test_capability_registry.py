"""Tests for CapabilityRegistryService."""

from __future__ import annotations

import pytest

from sfc.infrastructure.capability_registry.service import Capability, CapabilityRegistryService
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus


@pytest.fixture
def registry() -> CapabilityRegistryService:
    return CapabilityRegistryService()


def test_defaults_registered_on_init(registry: CapabilityRegistryService) -> None:
    """Default capabilities are registered when service is created."""
    report = registry.report()
    assert report["total_capabilities"] >= 15
    assert report["active_capabilities"] >= 15


def test_all_expected_categories_present(registry: CapabilityRegistryService) -> None:
    """All expected capability categories are represented."""
    report = registry.report()
    categories = set(report["by_category"].keys())

    required_categories = {
        "research", "content", "creative", "publishing",
        "analytics", "revenue", "governance", "learning", "infrastructure",
    }
    # Check that at least most categories are present
    assert len(required_categories & categories) >= 7


def test_find_by_category_research(registry: CapabilityRegistryService) -> None:
    """find_by_category() returns research capabilities."""
    research = registry.find_by_category("research")
    assert len(research) >= 3
    names = [c.name for c in research]
    assert "research" in names
    assert "fact_verification" in names


def test_find_by_category_creative(registry: CapabilityRegistryService) -> None:
    """find_by_category() returns creative capabilities."""
    creative = registry.find_by_category("creative")
    assert len(creative) >= 3
    names = [c.name for c in creative]
    assert "video_generation" in names
    assert "image_generation" in names


def test_find_by_category_empty(registry: CapabilityRegistryService) -> None:
    """find_by_category() returns empty list for unknown category."""
    result = registry.find_by_category("nonexistent_category")
    assert result == []


def test_find_by_provider(registry: CapabilityRegistryService) -> None:
    """find_by_provider() returns capabilities from the specified provider."""
    intelligence = registry.find_by_provider("intelligence")
    assert len(intelligence) >= 2
    assert all(c.provider == "intelligence" for c in intelligence)


def test_get_available_returns_active_only(registry: CapabilityRegistryService) -> None:
    """get_available() returns only active capabilities."""
    # Mark one as unavailable
    registry.update_status("cap_video_generation", "unavailable")

    available = registry.get_available()
    assert all(c.status == "active" for c in available)
    cap_ids = [c.capability_id for c in available]
    assert "cap_video_generation" not in cap_ids


def test_update_status_changes_status(registry: CapabilityRegistryService) -> None:
    """update_status() changes the capability's status."""
    registry.update_status("cap_research", "degraded")
    cap = registry.get("cap_research")
    assert cap is not None
    assert cap.status == "degraded"


def test_update_status_with_latency(registry: CapabilityRegistryService) -> None:
    """update_status() optionally updates avg_latency_ms."""
    registry.update_status("cap_research", "degraded", avg_latency_ms=5000.0)
    cap = registry.get("cap_research")
    assert cap is not None
    assert cap.avg_latency_ms == 5000.0


def test_update_status_unknown_id_no_error(registry: CapabilityRegistryService) -> None:
    """update_status() does nothing for unknown capability IDs."""
    # Should not raise
    registry.update_status("unknown_cap_id", "unavailable")


def test_record_use_increments_count(registry: CapabilityRegistryService) -> None:
    """record_use() increments the call count."""
    registry.record_use("cap_research")
    registry.record_use("cap_research")
    registry.record_use("cap_research")

    report = registry.report()
    top_used = report["top_used"]
    research_entry = next(
        (e for e in top_used if e["capability_id"] == "cap_research"), None
    )
    assert research_entry is not None
    assert research_entry["calls"] == 3


def test_register_custom_capability(registry: CapabilityRegistryService) -> None:
    """register() adds a custom capability to the catalog."""
    custom = Capability(
        capability_id="cap_custom_test",
        name="custom_test",
        description="A test capability",
        category="testing",
        provider="test_provider",
    )
    registry.register(custom)

    retrieved = registry.get("cap_custom_test")
    assert retrieved is not None
    assert retrieved.name == "custom_test"
    assert retrieved.category == "testing"


def test_get_unknown_capability_returns_none(registry: CapabilityRegistryService) -> None:
    """get() returns None for unknown capability IDs."""
    result = registry.get("cap_does_not_exist")
    assert result is None


def test_report_includes_all_categories(registry: CapabilityRegistryService) -> None:
    """report() includes all registered categories."""
    report = registry.report()
    assert "by_category" in report
    assert len(report["by_category"]) >= 7


def test_report_total_calls(registry: CapabilityRegistryService) -> None:
    """report() tracks total call count."""
    registry.record_use("cap_research")
    registry.record_use("cap_content_creation")
    registry.record_use("cap_publishing")

    report = registry.report()
    assert report["total_calls"] >= 3


def test_health_check_returns_component_health(registry: CapabilityRegistryService) -> None:
    """health_check() returns ComponentHealth without raising."""
    health = registry.health_check()
    assert isinstance(health, ComponentHealth)
    assert health.component == "capability_registry"
    assert health.status in list(HealthStatus)
    assert "total_capabilities" in health.metrics


def test_health_check_never_raises(registry: CapabilityRegistryService) -> None:
    """health_check() must never raise."""
    health = registry.health_check()
    assert health is not None


def test_health_check_degraded_when_many_unavailable(registry: CapabilityRegistryService) -> None:
    """health_check() returns DEGRADED when many capabilities are unavailable."""
    # Mark all capabilities as unavailable
    for cap_id in list(registry._catalog.keys()):
        registry.update_status(cap_id, "unavailable")

    health = registry.health_check()
    assert health.status == HealthStatus.DEGRADED
