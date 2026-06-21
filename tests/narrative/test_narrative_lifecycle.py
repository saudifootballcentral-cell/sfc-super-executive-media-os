"""Tests for Narrative Lifecycle Engine."""

import pytest

from sfc.narrative.lifecycle.models import (
    LifecycleBatch,
    NarrativeHealthMetrics,
    NarrativeLifecycleReport,
    NarrativeStage,
    NarrativeStageTransition,
    STAGE_ORDER,
)
from sfc.narrative.lifecycle.service import NarrativeLifecycleEngine, get_lifecycle_engine


class TestNarrativeStage:
    def test_all_stages_in_order(self):
        assert STAGE_ORDER[0] == NarrativeStage.SEED
        assert STAGE_ORDER[-1] == NarrativeStage.DEAD

    def test_stage_count(self):
        assert len(STAGE_ORDER) == 8


class TestNarrativeHealthMetrics:
    def test_create(self):
        m = NarrativeHealthMetrics(
            velocity=50.0,
            acceleration=10.0,
            volume=1000.0,
            influence=60.0,
            reach=70.0,
            sentiment=65.0,
            health_score=70.0,
        )
        assert m.health_score == 70.0

    def test_is_healthy_true(self):
        m = NarrativeHealthMetrics(
            velocity=50.0, acceleration=5.0, volume=500.0,
            influence=60.0, reach=60.0, sentiment=65.0, health_score=75.0,
        )
        assert m.is_healthy is True

    def test_is_healthy_false(self):
        m = NarrativeHealthMetrics(
            velocity=10.0, acceleration=-5.0, volume=100.0,
            influence=20.0, reach=25.0, sentiment=40.0, health_score=30.0,
        )
        assert m.is_healthy is False

    def test_is_at_risk(self):
        m = NarrativeHealthMetrics(
            velocity=20.0, acceleration=-2.0, volume=200.0,
            influence=35.0, reach=40.0, sentiment=45.0, health_score=45.0,
        )
        assert m.is_at_risk is True

    def test_not_at_risk(self):
        m = NarrativeHealthMetrics(
            velocity=50.0, acceleration=5.0, volume=500.0,
            influence=65.0, reach=70.0, sentiment=70.0, health_score=80.0,
        )
        assert m.is_at_risk is False


class TestNarrativeStageTransition:
    def test_create(self):
        t = NarrativeStageTransition(
            from_stage=NarrativeStage.SEED,
            to_stage=NarrativeStage.EMERGING,
            trigger="velocity_threshold",
            confidence=0.85,
        )
        assert t.from_stage == NarrativeStage.SEED
        assert t.confidence == 0.85

    def test_to_dict(self):
        t = NarrativeStageTransition(
            from_stage=NarrativeStage.GROWING,
            to_stage=NarrativeStage.ACCELERATING,
            trigger="volume_spike",
            confidence=0.75,
        )
        d = t.to_dict()
        assert isinstance(d, dict)
        assert "from_stage" in d


class TestNarrativeLifecycleReport:
    def test_to_dict(self):
        m = NarrativeHealthMetrics(
            velocity=50.0, acceleration=10.0, volume=500.0,
            influence=60.0, reach=70.0, sentiment=65.0, health_score=70.0,
        )
        r = NarrativeLifecycleReport(
            narrative_id="test_id",
            narrative_title="Test",
            current_stage=NarrativeStage.GROWING,
            metrics=m,
            time_in_current_stage_hours=12.0,
        )
        d = r.to_dict()
        assert d["narrative_id"] == "test_id"
        assert d["current_stage"] == NarrativeStage.GROWING

    def test_to_summary(self):
        m = NarrativeHealthMetrics(
            velocity=50.0, acceleration=10.0, volume=500.0,
            influence=60.0, reach=70.0, sentiment=65.0, health_score=70.0,
        )
        r = NarrativeLifecycleReport(
            narrative_id="test_id",
            narrative_title="Summary Test",
            current_stage=NarrativeStage.PEAK,
            metrics=m,
            time_in_current_stage_hours=6.0,
        )
        s = r.to_summary()
        assert "Summary Test" in s
        assert "PEAK" in s.upper() or "peak" in s.lower()


class TestNarrativeLifecycleEngine:
    @pytest.fixture
    def engine(self):
        return NarrativeLifecycleEngine()

    @pytest.mark.asyncio
    async def test_analyze_lifecycle(self, engine):
        report = await engine.analyze_lifecycle("test_narrative_001")
        assert isinstance(report, NarrativeLifecycleReport)
        assert report.narrative_id == "test_narrative_001"

    @pytest.mark.asyncio
    async def test_stage_is_valid(self, engine):
        report = await engine.analyze_lifecycle("narrative_x")
        assert report.current_stage in NarrativeStage.__members__.values()

    @pytest.mark.asyncio
    async def test_metrics_present(self, engine):
        report = await engine.analyze_lifecycle("narrative_y")
        assert isinstance(report.metrics, NarrativeHealthMetrics)
        assert report.metrics.health_score >= 0

    @pytest.mark.asyncio
    async def test_batch_analyze(self, engine):
        ids = ["n1", "n2", "n3"]
        batch = await engine.batch_analyze(ids)
        assert isinstance(batch, LifecycleBatch)
        assert len(batch.reports) == 3

    @pytest.mark.asyncio
    async def test_batch_to_dict(self, engine):
        batch = await engine.batch_analyze(["a", "b"])
        d = batch.to_dict()
        assert isinstance(d, dict)
        assert "reports" in d

    @pytest.mark.asyncio
    async def test_stage_history_list(self, engine):
        report = await engine.analyze_lifecycle("narrative_z")
        assert isinstance(report.stage_history, list)

    @pytest.mark.asyncio
    async def test_alerts_list(self, engine):
        report = await engine.analyze_lifecycle("narrative_alerts")
        assert isinstance(report.alerts, list)

    @pytest.mark.asyncio
    async def test_time_in_stage_positive(self, engine):
        report = await engine.analyze_lifecycle("narrative_time")
        assert report.time_in_current_stage_hours >= 0

    def test_singleton(self):
        a = get_lifecycle_engine()
        b = get_lifecycle_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_batch_categorizes(self, engine):
        batch = await engine.batch_analyze(["p1", "p2", "p3", "p4", "p5"])
        assert isinstance(batch.peak_narratives, list)
        assert isinstance(batch.emerging_narratives, list)
        assert isinstance(batch.declining_narratives, list)
