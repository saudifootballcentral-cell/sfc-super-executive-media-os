"""Tests for IntelligenceService — source verification, rumor classification, entity extraction."""

from __future__ import annotations

import pytest

from sfc.divisions.base import DivisionInput
from sfc.divisions.intelligence.service import IntelligenceService


def _make_input(
    task_type: str = "news",
    payload: dict | None = None,
    state: dict | None = None,
) -> DivisionInput:
    return DivisionInput(
        run_id="test-run-001",
        task_type=task_type,
        payload=payload or {},
        state_snapshot=state or {},
    )


class TestIntelligenceServiceLifecycle:
    async def test_initialize_and_shutdown(self) -> None:
        service = IntelligenceService()
        await service.initialize()
        await service.shutdown()

    def test_health_check_healthy_on_no_calls(self) -> None:
        service = IntelligenceService()
        health = service.health_check()
        assert health.status == "healthy"
        assert health.division == "intelligence"

    def test_describe_returns_string(self) -> None:
        service = IntelligenceService()
        assert len(service.describe()) > 5


class TestIntelligenceSourceVerification:
    async def test_verify_sources_with_two_sources_passes(self) -> None:
        service = IntelligenceService()
        result = await service.verify_sources("Ronaldo joins Al Nassr", ["BBC Sport", "Sky Sports"])
        assert result["passes_verification"] is True
        assert result["source_count"] == 2

    async def test_verify_sources_with_one_source_fails(self) -> None:
        service = IntelligenceService()
        result = await service.verify_sources("Transfer claim", ["Single Source"])
        assert result["passes_verification"] is False
        assert result["source_count"] == 1

    async def test_verify_sources_zero_sources_fails(self) -> None:
        service = IntelligenceService()
        result = await service.verify_sources("Unverified claim", [])
        assert result["passes_verification"] is False
        assert result["source_count"] == 0

    async def test_confidence_increases_with_more_sources(self) -> None:
        service = IntelligenceService()
        one = await service.verify_sources("claim", ["Source 1"])
        three = await service.verify_sources("claim", ["S1", "S2", "S3"])
        assert three["confidence_score"] > one["confidence_score"]


class TestIntelligenceRumorClassification:
    async def test_classify_confirmed_fact_not_rumor(self) -> None:
        service = IntelligenceService()
        result = await service.classify_rumor("Al Hilal officially signs new striker today")
        assert result["is_rumor"] is False
        assert result["label"] is None

    async def test_classify_rumor_keyword_detection(self) -> None:
        service = IntelligenceService()
        result = await service.classify_rumor("Sources say the player could reportedly join Al Nassr")
        assert result["is_rumor"] is True
        assert "RUMOR" in result["label"]

    async def test_rumor_has_lower_confidence(self) -> None:
        service = IntelligenceService()
        rumor = await service.classify_rumor("reportedly signing next week")
        fact = await service.classify_rumor("Al Hilal officially confirmed the signing")
        assert fact["confidence"] > rumor["confidence"]

    async def test_unconfirmed_label_format(self) -> None:
        service = IntelligenceService()
        result = await service.classify_rumor("sources say transfer could happen")
        if result["is_rumor"]:
            assert result["label"] == "RUMOR — unconfirmed"


class TestIntelligenceEntityExtraction:
    async def test_extract_known_saudi_clubs(self) -> None:
        service = IntelligenceService()
        result = await service.extract_entities("Al Hilal defeated Al Nassr 3-0 in the SPL")
        assert "Al Hilal" in result["clubs"]
        assert "Al Nassr" in result["clubs"]

    async def test_extract_competitions(self) -> None:
        service = IntelligenceService()
        result = await service.extract_entities("Saudi Pro League match day 12")
        assert "Saudi Pro League" in result["competitions"]

    async def test_extract_empty_text_returns_structure(self) -> None:
        service = IntelligenceService()
        result = await service.extract_entities("")
        assert "players" in result
        assert "clubs" in result
        assert "competitions" in result
        assert "coaches" in result


class TestIntelligenceConfidenceScoring:
    async def test_no_sources_low_confidence(self) -> None:
        service = IntelligenceService()
        inp = _make_input(payload={"headline": "test", "sources": []})
        result = await service.execute(inp)
        assert result.success
        conf = result.data["intelligence_report"]["confidence_score"]
        assert conf < 85.0

    async def test_three_sources_high_confidence(self) -> None:
        service = IntelligenceService()
        inp = _make_input(payload={
            "headline": "Al Hilal signs new striker",
            "sources": [
                {"name": "BBC Sport", "reliability_score": 90},
                {"name": "Sky Sports", "reliability_score": 88},
                {"name": "Al Kass TV", "reliability_score": 85},
            ],
        })
        result = await service.execute(inp)
        assert result.success
        conf = result.data["intelligence_report"]["confidence_score"]
        assert conf >= 85.0

    async def test_official_statement_boosts_confidence(self) -> None:
        service = IntelligenceService()
        inp_no_official = _make_input(payload={
            "headline": "test", "sources": [{"name": "S1"}, {"name": "S2"}]
        })
        inp_official = _make_input(payload={
            "headline": "test",
            "official_statement": True,
            "sources": [{"name": "S1"}, {"name": "S2"}],
        })
        r1 = await service.execute(inp_no_official)
        r2 = await service.execute(inp_official)
        c1 = r1.data["intelligence_report"]["confidence_score"]
        c2 = r2.data["intelligence_report"]["confidence_score"]
        assert c2 > c1


class TestIntelligenceExecute:
    async def test_execute_returns_report_and_sources(self) -> None:
        service = IntelligenceService()
        await service.initialize()
        inp = _make_input(payload={
            "headline": "Test headline",
            "sources": [{"name": "BBC"}, {"name": "Sky"}],
        })
        result = await service.execute(inp)
        assert result.success
        assert "intelligence_report" in result.data
        assert "verified_sources" in result.data

    async def test_execute_extracts_entities(self) -> None:
        service = IntelligenceService()
        inp = _make_input(payload={"headline": "Al Hilal wins Saudi Pro League"})
        result = await service.execute(inp)
        assert result.success
        entities = result.data["intelligence_report"].get("entities_detected", {})
        assert "clubs" in entities

    async def test_execute_handles_empty_payload_gracefully(self) -> None:
        service = IntelligenceService()
        result = await service.execute(_make_input())
        assert result.success is True

    async def test_health_check_degraded_on_high_error_rate(self) -> None:
        service = IntelligenceService()
        service._call_count = 10
        service._error_count = 8
        health = service.health_check()
        assert health.status in ("degraded", "unhealthy")
