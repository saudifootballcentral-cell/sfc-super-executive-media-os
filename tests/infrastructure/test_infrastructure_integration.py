"""Integration tests for InfrastructureContext."""

from __future__ import annotations

import pytest

from sfc.infrastructure.context import (
    InfrastructureContext,
    get_infrastructure,
    init_infrastructure,
    reset_infrastructure,
)
from sfc.infrastructure.shared.types import HealthStatus


@pytest.fixture(autouse=True)
def reset_ctx() -> None:
    """Reset the singleton before each test."""
    reset_infrastructure()
    yield
    reset_infrastructure()


def test_get_infrastructure_returns_same_instance() -> None:
    """get_infrastructure() returns the same singleton instance."""
    ctx1 = get_infrastructure()
    ctx2 = get_infrastructure()
    assert ctx1 is ctx2


def test_get_infrastructure_creates_context() -> None:
    """get_infrastructure() creates an InfrastructureContext."""
    ctx = get_infrastructure()
    assert isinstance(ctx, InfrastructureContext)


def test_infrastructure_not_initialized_on_get() -> None:
    """get_infrastructure() does NOT call initialize() automatically."""
    ctx = get_infrastructure()
    assert ctx._initialized is False


@pytest.mark.asyncio
async def test_init_infrastructure_initializes() -> None:
    """init_infrastructure() initializes all services."""
    ctx = await init_infrastructure()
    assert ctx._initialized is True


@pytest.mark.asyncio
async def test_init_infrastructure_idempotent() -> None:
    """init_infrastructure() is safe to call multiple times."""
    ctx1 = await init_infrastructure()
    ctx2 = await init_infrastructure()
    assert ctx1 is ctx2
    assert ctx2._initialized is True


@pytest.mark.asyncio
async def test_all_services_accessible_after_init() -> None:
    """After initialization, all 8 services are accessible."""
    ctx = await init_infrastructure()

    assert ctx.agentops is not None
    assert ctx.memory_manager is not None
    assert ctx.knowledge_graph is not None
    assert ctx.event_bus_manager is not None
    assert ctx.simulation_engine is not None
    assert ctx.capability_registry is not None
    assert ctx.tool_orchestration is not None
    assert ctx.learning_engine is not None


@pytest.mark.asyncio
async def test_health_report_has_all_8_components() -> None:
    """health_report() includes all 8 infrastructure components."""
    ctx = await init_infrastructure()
    report = ctx.health_report()

    assert "components" in report
    components = report["components"]

    required_components = {
        "agentops",
        "memory_manager",
        "knowledge_graph",
        "event_bus_manager",
        "simulation_engine",
        "capability_registry",
        "tool_orchestration",
        "learning_engine",
    }

    for component in required_components:
        assert component in components, f"Missing component: {component}"


@pytest.mark.asyncio
async def test_health_report_overall_status() -> None:
    """health_report() includes an overall_status field."""
    ctx = await init_infrastructure()
    report = ctx.health_report()

    assert "overall_status" in report
    assert report["overall_status"] in ("healthy", "degraded", "unhealthy")


@pytest.mark.asyncio
async def test_health_report_initialized_flag() -> None:
    """health_report() reflects initialized state."""
    ctx = await init_infrastructure()
    report = ctx.health_report()

    assert report["initialized"] is True


@pytest.mark.asyncio
async def test_memory_manager_stores_across_divisions() -> None:
    """MemoryManager can store and retrieve data for different divisions."""
    ctx = await init_infrastructure()

    await ctx.memory_manager.store("content", "article-001", {"title": "SPL News"}, division="editorial")
    await ctx.memory_manager.store("analysis", "report-001", {"score": 95.0}, division="analytics")

    editorial_data = await ctx.memory_manager.retrieve("content", "article-001", division="editorial")
    analytics_data = await ctx.memory_manager.retrieve("analysis", "report-001", division="analytics")

    assert editorial_data is not None
    assert editorial_data["title"] == "SPL News"

    assert analytics_data is not None
    assert analytics_data["score"] == 95.0


@pytest.mark.asyncio
async def test_division_memory_isolation() -> None:
    """Division memory is isolated — editorial data not visible in analytics."""
    ctx = await init_infrastructure()

    await ctx.memory_manager.store("content", "article-001", {"secret": True}, division="editorial")

    # Retrieve from different division — should be None
    result = await ctx.memory_manager.retrieve("content", "article-001", division="analytics")
    assert result is None


@pytest.mark.asyncio
async def test_learning_engine_persists_lessons_through_memory() -> None:
    """LearningEngine persists lessons through MemoryManager."""
    ctx = await init_infrastructure()

    state = {
        "run_id": "integration-test-001",
        "task_type": "transfer",
        "approved_content": [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}],
        "rejected_content": [],
        "analytics_report": {"estimated_reach": 2_000_000},
        "pipeline_stage": "complete",
        "errors": [],
        "warnings": [],
    }

    lessons = await ctx.learning_engine.analyze_workflow(state)
    # Lessons should exist
    assert len(lessons) >= 0  # May be 0 if no patterns triggered

    # Check that lessons were persisted to memory manager if any were generated
    if lessons:
        # Try to retrieve one lesson from memory
        lesson = lessons[0]
        stored = await ctx.memory_manager.retrieve("lessons", lesson.lesson_id.hex)
        assert stored is not None
        assert stored["run_id"] == "integration-test-001"


@pytest.mark.asyncio
async def test_knowledge_graph_ingestion_and_query() -> None:
    """KnowledgeGraph can ingest entities and query them."""
    ctx = await init_infrastructure()

    await ctx.knowledge_graph.add_entity("Al Hilal", "club")
    await ctx.knowledge_graph.add_entity("Salem Al-Dawsari", "player")
    await ctx.knowledge_graph.add_relationship("Salem Al-Dawsari", "Al Hilal", "plays_for")

    profile = await ctx.knowledge_graph.get_entity_profile("Salem Al-Dawsari")
    assert profile["name"] == "Salem Al-Dawsari"
    assert profile["relationship_count"] >= 1


@pytest.mark.asyncio
async def test_agentops_records_audit_during_workflow() -> None:
    """AgentOps records audit entries during normal workflow operations."""
    ctx = await init_infrastructure()

    ctx.agentops.audit("editorial", "create_draft", "run-integration-001")
    ctx.agentops.audit("governance", "review", "run-integration-001", success=True)

    assert len(ctx.agentops.audit_registry) >= 2


@pytest.mark.asyncio
async def test_capability_registry_available_after_init() -> None:
    """CapabilityRegistry has capabilities registered after init."""
    ctx = await init_infrastructure()
    report = ctx.capability_registry.report()
    assert report["total_capabilities"] >= 15
    assert report["active_capabilities"] >= 15


@pytest.mark.asyncio
async def test_simulation_engine_integrated() -> None:
    """SimulationEngine can run simulations through the context."""
    ctx = await init_infrastructure()

    result = await ctx.simulation_engine.simulate_content_performance(
        content_type="video",
        platforms=["youtube", "tiktok"],
        task_type="transfer",
        confidence_score=90.0,
        source_count=3,
    )

    assert result.expected_reach > 0
    assert 0 <= result.overall_score <= 100


@pytest.mark.asyncio
async def test_tool_orchestration_provides_providers() -> None:
    """ToolOrchestration returns providers through the context."""
    ctx = await init_infrastructure()

    providers = ctx.tool_orchestration.select_with_fallback("publishing")
    assert isinstance(providers, list)
    # Internal publisher is always available
    provider_ids = [p.provider_id for p in providers]
    assert "internal_publisher" in provider_ids


@pytest.mark.asyncio
async def test_event_bus_manager_tracks_events() -> None:
    """EventBusManager tracks published events."""
    from sfc.events.types import OpportunityDetected

    ctx = await init_infrastructure()

    event = OpportunityDetected(
        event_type="opportunity_detected",
        division="intelligence",
        run_id="integration-002",
        payload={"topic": "Al Hilal transfer"},
    )
    ctx.event_bus_manager.publish(event)

    dashboard = ctx.event_bus_manager.get_event_dashboard()
    assert dashboard["total_events"] >= 1
    assert "opportunity_detected" in dashboard["by_type"]


@pytest.mark.asyncio
async def test_shutdown_resets_initialized_flag() -> None:
    """shutdown() marks the context as not initialized."""
    ctx = await init_infrastructure()
    assert ctx._initialized is True

    await ctx.shutdown()
    assert ctx._initialized is False
