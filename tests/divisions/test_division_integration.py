"""Integration tests — full pipeline with real division services."""

from __future__ import annotations

import pytest

from sfc.divisions.analytics.service import AnalyticsService
from sfc.divisions.base import DivisionInput
from sfc.divisions.creative.service import CreativeService
from sfc.divisions.editorial.service import EditorialService
from sfc.divisions.governance.service import GovernanceService
from sfc.divisions.intelligence.service import IntelligenceService
from sfc.divisions.publishing.service import PublishingService
from sfc.divisions.revenue.service import RevenueService
from sfc.divisions.strategic_planning.service import StrategicPlanningService
from sfc.events.bus import EventBus


def _fresh_bus() -> EventBus:
    bus = EventBus()
    return bus


class TestDivisionImportsAndInstantiation:
    def test_all_services_importable(self) -> None:
        assert IntelligenceService is not None
        assert EditorialService is not None
        assert CreativeService is not None
        assert GovernanceService is not None
        assert PublishingService is not None
        assert AnalyticsService is not None
        assert RevenueService is not None
        assert StrategicPlanningService is not None

    def test_all_services_instantiable_without_args(self) -> None:
        IntelligenceService()
        EditorialService()
        CreativeService()
        GovernanceService()
        PublishingService()
        AnalyticsService()
        RevenueService()
        StrategicPlanningService()


class TestFullPipelineIntegration:
    """Run through Intelligence → Editorial → Governance → Publishing."""

    async def test_full_pipeline_with_two_sources(self) -> None:
        run_id = "integration-run-001"

        # 1. Intelligence
        intel_svc = IntelligenceService()
        await intel_svc.initialize()
        intel_result = await intel_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={
                "headline": "Al Hilal wins the Saudi Pro League",
                "sources": [
                    {"name": "Al Kass TV", "reliability_score": 90},
                    {"name": "SFC Official", "reliability_score": 95},
                    {"name": "Saudi Football", "reliability_score": 85},
                ],
                "official_statement": True,
            },
            state_snapshot={},
        ))
        assert intel_result.success
        intel_report = intel_result.data["intelligence_report"]
        sources = intel_result.data["verified_sources"]
        assert intel_report["confidence_score"] >= 85.0

        # 2. Editorial
        plan = {
            "task_type": "news",
            "content_types": ["article"],
            "platforms_targeted": ["website", "x"],
            "kpi_targets": {"reach": 50000},
        }
        editorial_svc = EditorialService()
        await editorial_svc.initialize()
        editorial_result = await editorial_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={},
            state_snapshot={
                "run_id": run_id,
                "task_type": "news",
                "task_payload": {},
                "intelligence_report": intel_report,
                "execution_plan": plan,
                "verified_sources": sources,
            },
        ))
        assert editorial_result.success
        drafts = editorial_result.data["content_drafts"]
        assert len(drafts) > 0

        # 3. Governance
        governance_svc = GovernanceService()
        await governance_svc.initialize()
        governance_result = await governance_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={},
            state_snapshot={
                "run_id": run_id,
                "content_drafts": drafts,
            },
        ))
        assert governance_result.success
        approved = governance_result.data["approved_content"]
        assert len(approved) > 0, "High-confidence content should be approved"

        # 4. Publishing
        publishing_svc = PublishingService()
        await publishing_svc.initialize()
        publishing_result = await publishing_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={},
            state_snapshot={
                "run_id": run_id,
                "approved_content": approved,
                "rejected_content": governance_result.data["rejected_content"],
                "revenue_signals": [],
                "execution_plan": plan,
            },
        ))
        assert publishing_result.success
        assert publishing_result.data["publish_results"]["published_count"] > 0

    async def test_pipeline_blocks_low_confidence_content(self) -> None:
        run_id = "integration-run-002"

        # Intelligence produces low confidence (no sources)
        intel_svc = IntelligenceService()
        intel_result = await intel_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={"headline": "Unverified rumor", "sources": []},
            state_snapshot={},
        ))
        intel_report = intel_result.data["intelligence_report"]
        # With 0 sources, confidence should be < 85
        assert intel_report["confidence_score"] < 85.0

        # Editorial creates drafts with that low confidence
        editorial_svc = EditorialService()
        editorial_result = await editorial_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={},
            state_snapshot={
                "run_id": run_id,
                "task_type": "news",
                "task_payload": {},
                "intelligence_report": intel_report,
                "execution_plan": {"content_types": ["article"], "platforms_targeted": ["website"]},
                "verified_sources": [],
            },
        ))
        drafts = editorial_result.data.get("content_drafts", [])

        # Governance must reject them all
        governance_svc = GovernanceService()
        governance_result = await governance_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="news",
            payload={},
            state_snapshot={"run_id": run_id, "content_drafts": drafts},
        ))
        approved = governance_result.data.get("approved_content", [])
        rejected = governance_result.data.get("rejected_content", [])

        if drafts:
            assert len(rejected) > 0, "Low confidence content must be rejected"
            assert len(approved) == 0, "No low-confidence content should be approved"


class TestEventPublishingAcrossDivisions:
    async def test_intelligence_publishes_brief_ready_event(self) -> None:
        import asyncio
        bus = _fresh_bus()
        received: list[str] = []

        def capture(event: object) -> None:
            received.append(getattr(event, "event_type", ""))

        bus.subscribe("intelligence_brief_ready", capture)

        import sfc.events.bus as bus_module
        original = bus_module._bus
        bus_module._bus = bus
        try:
            svc = IntelligenceService()
            await svc.execute(DivisionInput(
                run_id="test",
                task_type="news",
                payload={"headline": "test", "sources": [{"name": "BBC"}, {"name": "Sky"}]},
                state_snapshot={},
            ))
            await asyncio.sleep(0.05)
        finally:
            bus_module._bus = original

        assert "intelligence_brief_ready" in received

    async def test_governance_publishes_approved_event(self) -> None:
        import asyncio
        bus = _fresh_bus()
        received: list[str] = []

        def capture(event: object) -> None:
            received.append(getattr(event, "event_type", ""))

        bus.subscribe("governance_approved", capture)

        import sfc.events.bus as bus_module
        original = bus_module._bus
        bus_module._bus = bus
        try:
            svc = GovernanceService()
            await svc.execute(DivisionInput(
                run_id="test",
                task_type="news",
                payload={},
                state_snapshot={
                    "run_id": "test",
                    "content_drafts": [{
                        "content_id": "c1",
                        "title": "Test",
                        "body": "body",
                        "scores": {
                            "confidence_score": 90.0,
                            "risk_score": 10.0,
                            "source_count": 3,
                            "brand_alignment_score": 85.0,
                        },
                        "is_rumor": False,
                        "rumor_label": None,
                    }],
                },
            ))
            await asyncio.sleep(0.05)
        finally:
            bus_module._bus = original

        assert "governance_approved" in received


class TestMemoryPersistenceAcrossDivisionCalls:
    async def test_intelligence_persists_report_to_memory(self) -> None:
        from sfc.memory.division_memory import DivisionMemory
        from sfc.core.models import Division

        memory = DivisionMemory(Division.INTELLIGENCE)
        svc = IntelligenceService(memory_store=memory)
        await svc.execute(DivisionInput(
            run_id="mem-test-001",
            task_type="news",
            payload={"headline": "test", "sources": [{"name": "A"}, {"name": "B"}]},
            state_snapshot={},
        ))
        stored = memory.get("intel_mem-test-001")
        assert stored is not None
        assert "confidence_score" in stored

    async def test_editorial_persists_drafts_to_memory(self) -> None:
        from sfc.memory.division_memory import DivisionMemory
        from sfc.core.models import Division

        memory = DivisionMemory(Division.EDITORIAL)
        svc = EditorialService(memory_store=memory)
        await svc.execute(DivisionInput(
            run_id="mem-test-002",
            task_type="news",
            payload={},
            state_snapshot={
                "run_id": "mem-test-002",
                "task_type": "news",
                "task_payload": {},
                "intelligence_report": {"confidence_score": 90.0, "key_facts": ["fact"], "is_rumor": False, "rumor_label": None},
                "execution_plan": {"content_types": ["article"], "platforms_targeted": ["x"]},
                "verified_sources": [{"name": "A"}, {"name": "B"}],
            },
        ))
        stored = memory.get("drafts_mem-test-002")
        assert stored is not None
        assert len(stored) > 0

    async def test_governance_persists_reviews_to_memory(self) -> None:
        from sfc.memory.division_memory import DivisionMemory
        from sfc.core.models import Division

        memory = DivisionMemory(Division.GOVERNANCE)
        svc = GovernanceService(memory_store=memory)
        await svc.execute(DivisionInput(
            run_id="mem-test-003",
            task_type="news",
            payload={},
            state_snapshot={
                "run_id": "mem-test-003",
                "content_drafts": [{
                    "content_id": "c1",
                    "title": "Test",
                    "body": "body",
                    "scores": {
                        "confidence_score": 90.0,
                        "risk_score": 10.0,
                        "source_count": 3,
                        "brand_alignment_score": 85.0,
                    },
                    "is_rumor": False,
                    "rumor_label": None,
                }],
            },
        ))
        stored = memory.get("reviews_mem-test-003")
        assert stored is not None


class TestDivisionHealthChecks:
    def test_all_services_health_checks_never_raise(self) -> None:
        services = [
            IntelligenceService(),
            EditorialService(),
            CreativeService(),
            GovernanceService(),
            PublishingService(),
            AnalyticsService(),
            RevenueService(),
            StrategicPlanningService(),
        ]
        for svc in services:
            health = svc.health_check()
            assert health is not None
            assert health.status in ("healthy", "degraded", "unhealthy")


class TestStrategicPlanningToIntelligenceFlow:
    async def test_strategic_planning_output_feeds_intelligence(self) -> None:
        run_id = "flow-test-001"

        # 1. Strategic planning
        sp_svc = StrategicPlanningService()
        await sp_svc.initialize()
        sp_result = await sp_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="transfer",
            payload={},
            state_snapshot={
                "run_id": run_id,
                "task_type": "transfer",
                "task_payload": {},
                "executive_decision": {"priority": "high", "recommended_divisions": ["intelligence"]},
            },
        ))
        assert sp_result.success
        plan = sp_result.data["execution_plan"]

        # 2. Intelligence uses the plan context
        intel_svc = IntelligenceService()
        await intel_svc.initialize()
        intel_result = await intel_svc.execute(DivisionInput(
            run_id=run_id,
            task_type="transfer",
            payload={"sources": [{"name": "BBC"}, {"name": "Sky"}, {"name": "Goal"}]},
            state_snapshot={"run_id": run_id, "execution_plan": plan},
        ))
        assert intel_result.success
        assert intel_result.data["intelligence_report"]["research_complete"] is True
