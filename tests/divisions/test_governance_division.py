"""Tests for GovernanceService — full constitutional contract."""

from __future__ import annotations

import pytest

from sfc.divisions.base import DivisionInput
from sfc.divisions.governance.service import GovernanceService
from sfc.events.bus import EventBus


def _make_draft(
    confidence: float = 90.0,
    source_count: int = 3,
    brand_alignment: float = 85.0,
    risk_score: float = 10.0,
    is_rumor: bool = False,
    rumor_label: str | None = None,
    content_id: str = "test-001",
) -> dict:
    return {
        "content_id": content_id,
        "title": f"Test Content {content_id}",
        "body": "Test body content",
        "content_type": "article",
        "platforms": ["x", "website"],
        "scores": {
            "confidence_score": confidence,
            "risk_score": risk_score,
            "source_count": source_count,
            "brand_alignment_score": brand_alignment,
        },
        "is_rumor": is_rumor,
        "rumor_label": rumor_label,
        "division": "editorial",
    }


def _make_state(drafts: list) -> dict:
    return {
        "run_id": "test-run-001",
        "task_type": "news",
        "task_payload": {},
        "content_drafts": drafts,
        "approved_content": [],
        "rejected_content": [],
    }


class TestGovernanceServiceLifecycle:
    async def test_initialize_and_shutdown(self) -> None:
        service = GovernanceService()
        await service.initialize()
        await service.shutdown()

    async def test_health_check_always_returns(self) -> None:
        service = GovernanceService()
        health = service.health_check()
        assert health.status in ("healthy", "degraded", "unhealthy")
        assert health.division == "governance"

    def test_describe_returns_string(self) -> None:
        service = GovernanceService()
        desc = service.describe()
        assert isinstance(desc, str)
        assert len(desc) > 5


class TestGovernanceConstitutionalRules:
    async def test_content_with_all_scores_passing_is_approved(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft())
        assert review["approved"] is True
        assert review["escalated"] is False
        assert review["reasons"] == []

    async def test_insufficient_sources_rejected(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(source_count=1))
        assert review["approved"] is False
        assert any("source" in r.lower() for r in review["reasons"])

    async def test_zero_sources_rejected(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(source_count=0))
        assert review["approved"] is False

    async def test_exactly_two_sources_passes(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(source_count=2))
        assert review["approved"] is True

    async def test_confidence_84_rejected_and_escalated(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(confidence=84.9))
        assert review["approved"] is False
        assert review["escalated"] is True

    async def test_confidence_exactly_85_approved(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(confidence=85.0))
        assert review["approved"] is True

    async def test_confidence_100_approved(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(confidence=100.0))
        assert review["approved"] is True

    async def test_brand_alignment_below_70_rejected(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(brand_alignment=65.0))
        assert review["approved"] is False
        assert any("brand" in r.lower() for r in review["reasons"])

    async def test_brand_alignment_exactly_70_approved(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(brand_alignment=70.0))
        assert review["approved"] is True

    async def test_high_risk_score_escalated_but_not_blocked(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(risk_score=60.0))
        assert review["escalated"] is True
        # High risk does NOT block approval if all other checks pass
        # (risk_score > 50 escalates but doesn't add to violations that block)

    async def test_unlabeled_rumor_rejected(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(is_rumor=True, rumor_label=None))
        assert review["approved"] is False
        assert any("rumor" in r.lower() for r in review["reasons"])

    async def test_labeled_rumor_approved(self) -> None:
        service = GovernanceService()
        review = await service.review_content(
            _make_draft(is_rumor=True, rumor_label="RUMOR — unconfirmed")
        )
        assert review["approved"] is True

    async def test_non_rumor_with_no_label_approved(self) -> None:
        service = GovernanceService()
        review = await service.review_content(_make_draft(is_rumor=False, rumor_label=None))
        assert review["approved"] is True


class TestGovernanceExecute:
    async def test_execute_approves_valid_drafts(self) -> None:
        service = GovernanceService()
        await service.initialize()
        drafts = [_make_draft(content_id=f"c{i}") for i in range(3)]
        inp = DivisionInput(
            run_id="run-001",
            task_type="news",
            payload={},
            state_snapshot=_make_state(drafts),
        )
        result = await service.execute(inp)
        assert result.success is True
        assert len(result.data["approved_content"]) == 3
        assert len(result.data["rejected_content"]) == 0

    async def test_execute_rejects_low_confidence_drafts(self) -> None:
        service = GovernanceService()
        await service.initialize()
        drafts = [_make_draft(confidence=50.0)]
        inp = DivisionInput(
            run_id="run-002",
            task_type="news",
            payload={},
            state_snapshot=_make_state(drafts),
        )
        result = await service.execute(inp)
        assert result.success is True
        assert len(result.data["rejected_content"]) == 1
        assert len(result.data["approved_content"]) == 0

    async def test_execute_empty_drafts_returns_empty(self) -> None:
        service = GovernanceService()
        await service.initialize()
        inp = DivisionInput(
            run_id="run-003",
            task_type="news",
            payload={},
            state_snapshot=_make_state([]),
        )
        result = await service.execute(inp)
        assert result.success is True
        assert result.data["approved_content"] == []
        assert result.data["rejected_content"] == []

    async def test_execute_publishes_events(self) -> None:
        import asyncio
        from sfc.events.bus import EventBus
        bus = EventBus()
        collected: list[str] = []

        def collect(event: object) -> None:
            collected.append(getattr(event, "event_type", ""))

        bus.subscribe("governance_approved", collect)

        service = GovernanceService()
        await service.initialize()
        drafts = [_make_draft()]
        inp = DivisionInput(
            run_id="run-004",
            task_type="news",
            payload={},
            state_snapshot=_make_state(drafts),
        )
        # Patch bus
        import sfc.events.bus as bus_module
        original = bus_module._bus
        bus_module._bus = bus
        try:
            await service.execute(inp)
            await asyncio.sleep(0.05)  # Let async handler tasks complete
        finally:
            bus_module._bus = original

        assert "governance_approved" in collected


class TestGovernanceValidate:
    async def test_validate_passing_content(self) -> None:
        service = GovernanceService()
        result = await service.validate(_make_draft())
        assert result.valid is True
        assert result.score > 80.0

    async def test_validate_failing_content(self) -> None:
        service = GovernanceService()
        result = await service.validate(_make_draft(confidence=40.0, source_count=0))
        assert result.valid is False
        assert len(result.reasons) >= 2


class TestGovernanceReport:
    async def test_report_returns_division_report(self) -> None:
        service = GovernanceService()
        report = await service.report()
        assert report.division == "governance"
        assert "total_approved" in report.metrics
