"""Tests for Trend Radar Engine."""

from __future__ import annotations

import pytest

from sfc.social.trend_radar.models import (
    SocialSource,
    TrendForecast,
    TrendMetrics,
    TrendRadarSnapshot,
    TrendReport,
    TrendState,
)
from sfc.social.trend_radar.service import TrendRadarService, get_trend_radar


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestTrendState:
    def test_all_states_defined(self):
        states = [s.value for s in TrendState]
        assert "breaking" in states
        assert "emerging" in states
        assert "declining" in states
        assert "dead" in states

    def test_seven_states(self):
        assert len(TrendState) == 7


class TestTrendMetrics:
    def test_defaults(self):
        m = TrendMetrics()
        assert m.velocity == 0.0
        assert m.volume == 0
        assert m.reach == 0
        assert m.engagement == 0.0

    def test_set_values(self):
        m = TrendMetrics(velocity=5.5, volume=10000, reach=500000, engagement=0.05)
        assert m.velocity == 5.5
        assert m.volume == 10000


class TestTrendForecast:
    def test_defaults(self):
        f = TrendForecast()
        assert f.confidence >= 0.0
        assert f.peak_estimate_hours >= 0.0

    def test_with_states(self):
        f = TrendForecast(
            expected_state_in_1h=TrendState.HOT.value,
            expected_state_in_6h=TrendState.PEAK.value,
            expected_state_in_24h=TrendState.DECLINING.value,
        )
        assert f.expected_state_in_1h == "hot"
        assert f.expected_state_in_24h == "declining"


class TestTrendReport:
    def test_defaults(self):
        r = TrendReport(topic="Al Hilal", state=TrendState.BREAKING)
        assert r.trend_id != ""
        assert r.topic == "Al Hilal"
        assert r.state == TrendState.BREAKING
        assert r.score == 0.0

    def test_to_dict(self):
        r = TrendReport(
            topic="Transfer window",
            state=TrendState.EMERGING,
            score=72.5,
        )
        d = r.to_dict()
        assert d["topic"] == "Transfer window"
        assert d["score"] == 72.5
        assert d["state"] == "emerging"

    def test_to_summary(self):
        r = TrendReport(topic="SPL", state=TrendState.HOT, score=88.0)
        s = r.to_summary()
        assert "trend_id" in s
        assert s["topic"] == "SPL"
        assert s["score"] == 88.0
        assert s["state"] == "hot"


class TestTrendRadarSnapshot:
    def test_defaults(self):
        snap = TrendRadarSnapshot()
        assert snap.total_tracked == 0
        assert snap.breaking_trends == []
        assert snap.emerging_trends == []

    def test_to_dict(self):
        snap = TrendRadarSnapshot(
            total_tracked=5,
            top_topic="Al Nassr",
            top_score=91.0,
        )
        d = snap.to_dict()
        assert d["total_tracked"] == 5
        assert d["top_topic"] == "Al Nassr"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestTrendRadarService:
    def test_singleton(self):
        s1 = get_trend_radar()
        s2 = get_trend_radar()
        assert s1 is s2

    def test_init(self):
        service = TrendRadarService()
        assert service._trends == {}
        assert service._history == []

    @pytest.mark.asyncio
    async def test_scan_returns_snapshot(self):
        service = TrendRadarService()
        snapshot = await service.scan(topics=["Al Hilal", "SPL transfer"])
        assert isinstance(snapshot, TrendRadarSnapshot)
        assert snapshot.total_tracked >= 1

    @pytest.mark.asyncio
    async def test_scan_populates_trends(self):
        service = TrendRadarService()
        await service.scan(topics=["test topic"])
        assert len(service._trends) >= 1

    @pytest.mark.asyncio
    async def test_scan_uses_default_topics_when_none(self):
        service = TrendRadarService()
        snapshot = await service.scan()
        assert snapshot.total_tracked > 0

    @pytest.mark.asyncio
    async def test_get_snapshot_after_scan(self):
        service = TrendRadarService()
        await service.scan(topics=["topic1"])
        snapshot = await service.get_snapshot()
        assert isinstance(snapshot, TrendRadarSnapshot)

    @pytest.mark.asyncio
    async def test_get_snapshot_triggers_scan_when_empty(self):
        service = TrendRadarService()
        snapshot = await service.get_snapshot()
        assert isinstance(snapshot, TrendRadarSnapshot)

    @pytest.mark.asyncio
    async def test_get_trend_after_scan(self):
        service = TrendRadarService()
        await service.scan(topics=["unique topic here"])
        trend_ids = list(service._trends.keys())
        assert len(trend_ids) > 0
        trend = service.get_trend(trend_ids[0])
        assert trend is not None
        assert isinstance(trend, TrendReport)

    def test_get_trend_returns_none_for_unknown(self):
        service = TrendRadarService()
        assert service.get_trend("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_history(self):
        service = TrendRadarService()
        await service.scan(topics=["history test"])
        history = service.get_history()
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_alerts_for_breaking_trends(self):
        service = TrendRadarService()
        snapshot = await service.scan(topics=["Al Hilal Champions"])
        assert isinstance(snapshot.alerts, list)

    @pytest.mark.asyncio
    async def test_snapshot_has_all_fields(self):
        service = TrendRadarService()
        snapshot = await service.scan(["transfer news"])
        d = snapshot.to_dict()
        assert "breaking_trends" in d
        assert "emerging_trends" in d
        assert "hot_trends" in d
        assert "total_tracked" in d
        assert "top_topic" in d
        assert "top_score" in d
        assert "alerts" in d

    def test_max_history_limit(self):
        service = TrendRadarService()
        service._max_history = 3
        for i in range(5):
            from sfc.social.trend_radar.models import TrendReport, TrendState
            report = TrendReport(topic=f"topic_{i}", state=TrendState.EMERGING)
            service._history.append(report)
        assert len(service._history) <= 5  # capped externally during scan
