"""Tests for Narrative Intelligence Engine."""

from __future__ import annotations

import pytest

from sfc.social.narrative.models import (
    Narrative,
    NarrativeCategory,
    NarrativeLifecycle,
    NarrativeMap,
    NarrativeMetrics,
    NarrativeReport,
)
from sfc.social.narrative.service import NarrativeIntelligenceService, get_narrative_service


class TestNarrativeLifecycle:
    def test_five_states(self):
        assert len(NarrativeLifecycle) == 5

    def test_state_values(self):
        values = {s.value for s in NarrativeLifecycle}
        assert "emerging" in values
        assert "peaking" in values
        assert "dormant" in values


class TestNarrativeCategory:
    def test_categories(self):
        values = {c.value for c in NarrativeCategory}
        assert "player" in values
        assert "transfer" in values
        assert "national_team" in values
        assert "tournament" in values


class TestNarrativeMetrics:
    def test_defaults(self):
        m = NarrativeMetrics()
        assert m.score == 0.0
        assert m.sentiment == 0.0
        assert m.influence == 0.0

    def test_score_bounds(self):
        m = NarrativeMetrics(score=75.0, sentiment=0.5, influence=0.8)
        assert 0 <= m.score <= 100
        assert -1 <= m.sentiment <= 1


class TestNarrative:
    def test_creation(self):
        n = Narrative(
            title="Al Hilal Champions League",
            lifecycle=NarrativeLifecycle.GROWING,
            category=NarrativeCategory.CLUB,
        )
        assert n.narrative_id != ""
        assert n.title == "Al Hilal Champions League"

    def test_to_dict(self):
        n = Narrative(
            title="Transfer Saga",
            lifecycle=NarrativeLifecycle.PEAKING,
            category=NarrativeCategory.TRANSFER,
        )
        d = n.to_dict()
        assert d["title"] == "Transfer Saga"
        assert d["lifecycle"] == "peaking"
        assert d["category"] == "transfer"

    def test_entities_list(self):
        n = Narrative(
            title="Player Move",
            lifecycle=NarrativeLifecycle.EMERGING,
            category=NarrativeCategory.PLAYER,
            entities=["Ronaldo", "Al Nassr"],
        )
        assert "Ronaldo" in n.entities


class TestNarrativeMap:
    def test_defaults(self):
        nm = NarrativeMap()
        assert nm.narratives == []
        assert nm.emerging_count == 0

    def test_to_dict(self):
        nm = NarrativeMap(emerging_count=3, declining_count=1)
        d = nm.to_dict()
        assert d["emerging_count"] == 3


class TestNarrativeReport:
    def test_to_dict(self):
        nm = NarrativeMap()
        r = NarrativeReport(narrative_map=nm)
        d = r.to_dict()
        assert "narrative_map" in d
        assert "top_narratives" in d


class TestNarrativeIntelligenceService:
    def test_singleton(self):
        assert get_narrative_service() is get_narrative_service()

    def test_init(self):
        service = NarrativeIntelligenceService()
        assert service._narratives == {}
        assert service._history == []

    @pytest.mark.asyncio
    async def test_detect_narratives(self):
        service = NarrativeIntelligenceService()
        narratives = await service.detect_narratives(
            topics=["Al Hilal dominance", "transfer window"]
        )
        assert len(narratives) >= 1
        assert all(isinstance(n, Narrative) for n in narratives)

    @pytest.mark.asyncio
    async def test_detect_uses_default_topics(self):
        service = NarrativeIntelligenceService()
        narratives = await service.detect_narratives()
        assert len(narratives) > 0

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = NarrativeIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report, NarrativeReport)
        assert isinstance(report.narrative_map, NarrativeMap)

    @pytest.mark.asyncio
    async def test_generate_report_with_narratives(self):
        service = NarrativeIntelligenceService()
        narratives = await service.detect_narratives(topics=["Saudi football"])
        report = await service.generate_report(narratives=narratives)
        assert len(report.top_narratives) >= 1

    @pytest.mark.asyncio
    async def test_build_narrative_map(self):
        service = NarrativeIntelligenceService()
        narratives = await service.detect_narratives(topics=["topic1", "topic2"])
        nm = await service.build_narrative_map(narratives)
        assert isinstance(nm, NarrativeMap)
        assert nm.emerging_count + nm.declining_count <= len(narratives)

    @pytest.mark.asyncio
    async def test_get_history(self):
        service = NarrativeIntelligenceService()
        await service.detect_narratives(["test"])
        history = service.get_history()
        assert isinstance(history, list)

    def test_classify_topic_transfer(self):
        service = NarrativeIntelligenceService()
        cat = service._classify_topic("Ronaldo transfer deal")
        assert cat == NarrativeCategory.TRANSFER

    def test_classify_topic_national(self):
        service = NarrativeIntelligenceService()
        cat = service._classify_topic("green falcons World Cup")
        assert cat == NarrativeCategory.NATIONAL_TEAM

    def test_classify_topic_club(self):
        service = NarrativeIntelligenceService()
        cat = service._classify_topic("Al Hilal club news")
        assert cat == NarrativeCategory.CLUB

    def test_detect_conflicts_no_conflicts(self):
        service = NarrativeIntelligenceService()
        n1 = Narrative(
            title="A",
            lifecycle=NarrativeLifecycle.GROWING,
            category=NarrativeCategory.GENERAL,
            metrics=NarrativeMetrics(sentiment=0.5),
        )
        n2 = Narrative(
            title="B",
            lifecycle=NarrativeLifecycle.GROWING,
            category=NarrativeCategory.GENERAL,
            metrics=NarrativeMetrics(sentiment=0.4),
        )
        conflicts = service._detect_conflicts([n1, n2])
        assert conflicts == []
