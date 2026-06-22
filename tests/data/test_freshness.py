"""Data freshness scorer tests — Package 10A."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sfc.data.freshness import DataFreshnessScorer


class TestDataFreshnessScorer:
    def setup_method(self):
        self.scorer = DataFreshnessScorer(max_age_hours=24.0)
        self.now = datetime(2026, 6, 22, 12, 0, 0)

    def test_just_collected_is_100(self):
        collected = self.now
        score = self.scorer.score(collected, now=self.now)
        assert score == 100.0

    def test_fully_stale_is_0(self):
        collected = self.now - timedelta(hours=24)
        score = self.scorer.score(collected, now=self.now)
        assert score == 0.0

    def test_half_life_is_50(self):
        collected = self.now - timedelta(hours=12)
        score = self.scorer.score(collected, now=self.now)
        assert abs(score - 50.0) < 1.0

    def test_score_decreases_with_age(self):
        scores = []
        for h in [0, 6, 12, 18, 24]:
            collected = self.now - timedelta(hours=h)
            scores.append(self.scorer.score(collected, now=self.now))
        assert scores == sorted(scores, reverse=True)

    def test_future_collected_returns_100(self):
        collected = self.now + timedelta(hours=1)
        score = self.scorer.score(collected, now=self.now)
        assert score == 100.0

    def test_is_fresh_above_threshold(self):
        collected = self.now - timedelta(hours=6)
        assert self.scorer.is_fresh(collected, threshold=50.0) is True

    def test_is_fresh_below_threshold(self):
        collected = self.now - timedelta(hours=18)
        assert self.scorer.is_fresh(collected, threshold=50.0) is False

    def test_ttl_just_collected_is_max(self):
        collected = self.now
        ttl = self.scorer.ttl_seconds(collected, now=self.now)
        assert abs(ttl - 86400.0) < 1.0

    def test_ttl_fully_stale_is_zero(self):
        collected = self.now - timedelta(hours=24)
        ttl = self.scorer.ttl_seconds(collected, now=self.now)
        assert ttl == 0.0

    def test_custom_max_age(self):
        scorer = DataFreshnessScorer(max_age_hours=1.0)
        collected = self.now - timedelta(minutes=30)
        score = scorer.score(collected, now=self.now)
        assert abs(score - 50.0) < 1.0

    def test_score_returns_float(self):
        score = self.scorer.score(self.now, now=self.now)
        assert isinstance(score, float)

    def test_beyond_stale_clamped_to_zero(self):
        collected = self.now - timedelta(hours=48)
        score = self.scorer.score(collected, now=self.now)
        assert score == 0.0
