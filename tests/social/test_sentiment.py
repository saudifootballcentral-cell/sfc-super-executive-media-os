"""Tests for Fan Sentiment Engine."""

from __future__ import annotations

import pytest

from sfc.social.sentiment.models import (
    FanPulseReport,
    SentimentCategory,
    SentimentMetrics,
    SentimentTarget,
    SentimentTarget_,
)
from sfc.social.sentiment.service import FanSentimentService, get_sentiment_service


class TestSentimentCategory:
    def test_three_categories(self):
        assert len(SentimentCategory) == 3
        values = {c.value for c in SentimentCategory}
        assert "positive" in values
        assert "neutral" in values
        assert "negative" in values


class TestSentimentTargetEnum:
    def test_six_targets(self):
        assert len(SentimentTarget) == 6
        values = {t.value for t in SentimentTarget}
        assert "player" in values
        assert "coach" in values
        assert "club" in values
        assert "national_team" in values


class TestSentimentMetrics:
    def test_defaults(self):
        m = SentimentMetrics()
        assert m.score == 0.0
        assert m.momentum == 0.0
        assert m.sample_size == 0

    def test_category_positive(self):
        m = SentimentMetrics(score=50.0)
        assert m.category == SentimentCategory.POSITIVE

    def test_category_negative(self):
        m = SentimentMetrics(score=-40.0)
        assert m.category == SentimentCategory.NEGATIVE

    def test_category_neutral(self):
        m = SentimentMetrics(score=0.0)
        assert m.category == SentimentCategory.NEUTRAL

    def test_category_boundary_positive(self):
        m = SentimentMetrics(score=21.0)
        assert m.category == SentimentCategory.POSITIVE

    def test_category_boundary_negative(self):
        m = SentimentMetrics(score=-21.0)
        assert m.category == SentimentCategory.NEGATIVE


class TestSentimentTarget_:
    def test_creation(self):
        t = SentimentTarget_(
            entity_name="Al Hilal",
            target_type=SentimentTarget.CLUB,
        )
        assert t.entity_id != ""
        assert t.entity_name == "Al Hilal"

    def test_to_dict(self):
        t = SentimentTarget_(
            entity_name="Ronaldo",
            target_type=SentimentTarget.PLAYER,
            metrics=SentimentMetrics(score=80.0),
        )
        d = t.to_dict()
        assert d["entity_name"] == "Ronaldo"
        assert d["target_type"] == "player"
        assert d["metrics"]["score"] == 80.0


class TestFanPulseReport:
    def test_defaults(self):
        r = FanPulseReport()
        assert r.overall_score == 0.0
        assert r.overall_category == SentimentCategory.NEUTRAL
        assert r.tracked_entities == []

    def test_to_dict(self):
        r = FanPulseReport(overall_score=45.0, overall_category=SentimentCategory.POSITIVE)
        d = r.to_dict()
        assert d["overall_score"] == 45.0

    def test_to_dashboard_data(self):
        r = FanPulseReport(overall_score=30.0, overall_category=SentimentCategory.POSITIVE)
        data = r.to_dashboard_data()
        assert "overall_score" in data
        assert "overall_category" in data
        assert "entity_count" in data
        assert data["overall_category"] == "positive"


class TestFanSentimentService:
    def test_singleton(self):
        assert get_sentiment_service() is get_sentiment_service()

    def test_init(self):
        service = FanSentimentService()
        assert service._targets == {}
        assert service._history == []

    @pytest.mark.asyncio
    async def test_analyze_defaults(self):
        service = FanSentimentService()
        targets = await service.analyze()
        assert len(targets) > 0
        assert all(isinstance(t, SentimentTarget_) for t in targets)

    @pytest.mark.asyncio
    async def test_analyze_specific_entities(self):
        service = FanSentimentService()
        targets = await service.analyze(entity_ids=["al_hilal_club", "al_nassr_club"])
        assert len(targets) == 2

    @pytest.mark.asyncio
    async def test_generate_fan_pulse_report(self):
        service = FanSentimentService()
        report = await service.generate_fan_pulse_report()
        assert isinstance(report, FanPulseReport)
        assert report.overall_category in list(SentimentCategory)

    @pytest.mark.asyncio
    async def test_report_with_targets(self):
        service = FanSentimentService()
        targets = await service.analyze(entity_ids=["test_entity"])
        report = await service.generate_fan_pulse_report(targets=targets)
        assert len(report.tracked_entities) == 1

    @pytest.mark.asyncio
    async def test_get_alerts_empty_when_no_crisis(self):
        service = FanSentimentService()
        # Clear any existing targets
        service._targets = {}
        alerts = await service.get_alerts()
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_get_alerts_with_crisis(self):
        service = FanSentimentService()
        crisis_target = SentimentTarget_(
            entity_name="Crisis Entity",
            target_type=SentimentTarget.CLUB,
            metrics=SentimentMetrics(score=-70.0),
        )
        service._targets["crisis_entity"] = crisis_target
        alerts = await service.get_alerts()
        assert len(alerts) >= 1

    @pytest.mark.asyncio
    async def test_get_history(self):
        service = FanSentimentService()
        await service.generate_fan_pulse_report()
        history = service.get_history()
        assert isinstance(history, list)

    def test_infer_target_type_player(self):
        service = FanSentimentService()
        t = service._infer_target_type("ronaldo_player")
        assert t == SentimentTarget.PLAYER

    def test_infer_target_type_club(self):
        service = FanSentimentService()
        t = service._infer_target_type("al_hilal_club")
        assert t == SentimentTarget.CLUB

    def test_infer_target_type_national(self):
        service = FanSentimentService()
        t = service._infer_target_type("green_falcons_national_team")
        assert t == SentimentTarget.NATIONAL_TEAM

    def test_get_target_returns_none(self):
        service = FanSentimentService()
        assert service.get_target("nonexistent") is None

    @pytest.mark.asyncio
    async def test_report_overall_category_computed(self):
        service = FanSentimentService()
        targets = [
            SentimentTarget_(
                entity_name=f"Entity {i}",
                target_type=SentimentTarget.CLUB,
                metrics=SentimentMetrics(score=50.0),
            )
            for i in range(3)
        ]
        report = await service.generate_fan_pulse_report(targets=targets)
        assert report.overall_category == SentimentCategory.POSITIVE
