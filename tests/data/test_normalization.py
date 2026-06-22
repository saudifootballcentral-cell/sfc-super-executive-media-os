"""Data normalizer tests — Package 10A."""

from __future__ import annotations

from datetime import datetime

import pytest

from sfc.data.normalizer import DataNormalizer


class TestDataNormalizer:
    def setup_method(self):
        self.normalizer = DataNormalizer()

    def test_normalize_always_sets_data_source(self):
        point = self.normalizer.normalize({"term": "AlHilal"}, "x_api")
        assert point.data_source == "x_api"

    def test_normalize_always_sets_confidence_score(self):
        point = self.normalizer.normalize({}, "youtube_api")
        assert point.confidence_score == 95.0

    def test_normalize_always_sets_freshness_score(self):
        point = self.normalizer.normalize({}, "rss")
        assert 0.0 <= point.freshness_score <= 100.0

    def test_normalize_fixture_source_lower_confidence(self):
        point = self.normalizer.normalize({}, "mock_fixture")
        assert point.confidence_score == 60.0

    def test_normalize_term_field(self):
        point = self.normalizer.normalize({"term": "#SPL"}, "x_api")
        assert point.term == "#SPL"

    def test_normalize_keyword_fallback(self):
        point = self.normalizer.normalize({"keyword": "AlNassr"}, "x_api")
        assert point.term == "AlNassr"

    def test_normalize_tweet_volume(self):
        point = self.normalizer.normalize({"tweet_volume": 12500}, "x_api")
        assert point.tweet_volume == 12500

    def test_normalize_volume_fallback(self):
        point = self.normalizer.normalize({"volume": 8000}, "google_trends")
        assert point.tweet_volume == 8000

    def test_normalize_views(self):
        point = self.normalizer.normalize({"views": 50000}, "youtube_api")
        assert point.views == 50000

    def test_normalize_headline_from_title(self):
        point = self.normalizer.normalize({"title": "Al Hilal wins"}, "rss")
        assert point.headline == "Al Hilal wins"

    def test_normalize_summary(self):
        point = self.normalizer.normalize({"summary": "Short summary"}, "rss")
        assert point.summary == "Short summary"

    def test_normalize_tags(self):
        point = self.normalizer.normalize({"tags": ["SPL", "AlHilal"]}, "rss")
        assert "SPL" in point.tags

    def test_normalize_computes_content_hash(self):
        point = self.normalizer.normalize({"term": "test"}, "x_api")
        assert len(point.content_hash) > 0

    def test_normalize_batch_returns_list(self):
        raws = [{"term": "a"}, {"term": "b"}, {"term": "c"}]
        points = self.normalizer.normalize_batch(raws, "x_api")
        assert len(points) == 3

    def test_normalize_batch_all_have_data_source(self):
        raws = [{"term": "x"}, {"term": "y"}]
        points = self.normalizer.normalize_batch(raws, "rss")
        assert all(p.data_source == "rss" for p in points)

    def test_normalize_collected_at_string_parses(self):
        point = self.normalizer.normalize(
            {"collected_at": "2026-06-22T12:00:00"}, "x_api"
        )
        assert isinstance(point.collected_at, datetime)

    def test_normalize_collected_at_missing_uses_now(self):
        before = datetime.utcnow()
        point = self.normalizer.normalize({}, "x_api")
        assert point.collected_at >= before

    def test_normalize_influencer_fields(self):
        point = self.normalizer.normalize(
            {"influence_score": 85.0, "trust_score": 79.0, "follower_count": 500000},
            "x_api",
        )
        assert point.influence_score == 85.0
        assert point.trust_score == 79.0
        assert point.follower_count == 500000

    def test_normalize_audience_fields(self):
        point = self.normalizer.normalize(
            {"size": 1000000, "growth_rate": 8.5, "retention_rate": 0.72},
            "mock_fixture",
        )
        assert point.segment_size == 1000000
        assert point.growth_rate == 8.5
        assert point.retention_rate == 0.72
