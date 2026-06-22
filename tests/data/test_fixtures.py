"""Fixture loader tests — Package 10A."""

from __future__ import annotations

import pytest

from sfc.data.fixtures.loader import FixtureLoader, get_fixture_loader


class TestFixtureLoader:
    def setup_method(self):
        self.loader = FixtureLoader()

    def test_load_saudi_trends_returns_dict(self):
        data = self.loader.load("saudi_trends")
        assert isinstance(data, dict)
        assert "trends" in data

    def test_load_saudi_sentiment_returns_dict(self):
        data = self.loader.load("saudi_sentiment")
        assert isinstance(data, dict)
        assert "entities" in data

    def test_load_saudi_analytics_returns_dict(self):
        data = self.loader.load("saudi_analytics")
        assert isinstance(data, dict)
        assert "youtube_channel" in data

    def test_load_saudi_news_returns_dict(self):
        data = self.loader.load("saudi_news")
        assert isinstance(data, dict)
        assert "items" in data

    def test_load_with_json_extension_works(self):
        data = self.loader.load("saudi_trends.json")
        assert isinstance(data, dict)

    def test_load_missing_file_returns_empty_dict(self):
        data = self.loader.load("nonexistent_fixture")
        assert data == {}

    def test_get_trends_returns_list(self):
        trends = self.loader.get_trends()
        assert isinstance(trends, list)
        assert len(trends) > 0

    def test_trends_have_required_fields(self):
        trends = self.loader.get_trends()
        for t in trends:
            assert "term" in t
            assert "tweet_volume" in t
            assert "velocity" in t
            assert "sentiment" in t

    def test_get_topic_scores_returns_dict(self):
        scores = self.loader.get_topic_scores()
        assert isinstance(scores, dict)
        assert len(scores) > 0

    def test_topic_scores_have_required_fields(self):
        scores = self.loader.get_topic_scores()
        for topic, data in scores.items():
            assert "score" in data
            assert "velocity" in data
            assert "volume" in data

    def test_get_sentiment_known_entity(self):
        data = self.loader.get_sentiment("Al Hilal")
        assert "sentiment_score" in data
        assert isinstance(data["sentiment_score"], (int, float))

    def test_get_sentiment_unknown_entity_returns_default(self):
        data = self.loader.get_sentiment("Unknown Entity XYZ")
        assert "sentiment_score" in data

    def test_get_analytics_channel_returns_dict(self):
        data = self.loader.get_analytics_channel()
        assert "subscriber_count" in data
        assert int(data["subscriber_count"]) > 0

    def test_get_analytics_video_default(self):
        data = self.loader.get_analytics_video("default")
        assert "views" in data
        assert int(data["views"]) > 0

    def test_get_analytics_video_short(self):
        data = self.loader.get_analytics_video("short")
        assert int(data["views"]) > int(self.loader.get_analytics_video("default")["views"])

    def test_get_x_post_metrics_default(self):
        data = self.loader.get_x_post_metrics("default")
        assert "views" in data
        assert "engagement_rate" in data

    def test_get_influencer_profile_known(self):
        data = self.loader.get_influencer_profile("@AlHilalFC")
        assert "influence_score" in data
        assert float(data["influence_score"]) > 0

    def test_get_influencer_profile_unknown_returns_default(self):
        data = self.loader.get_influencer_profile("@unknown_handle")
        assert "influence_score" in data

    def test_get_audience_segment(self):
        data = self.loader.get_audience_segment("core_football_fans")
        assert "size" in data
        assert int(data["size"]) > 0

    def test_get_news_items_returns_list(self):
        items = self.loader.get_news_items()
        assert isinstance(items, list)
        assert len(items) > 0

    def test_news_items_have_required_fields(self):
        items = self.loader.get_news_items()
        for item in items:
            assert "headline" in item
            assert "source_url" in item

    def test_fixture_data_source_is_mock_fixture(self):
        data = self.loader.load("saudi_trends")
        assert data.get("data_source") == "mock_fixture"

    def test_singleton_returns_same_instance(self):
        a = get_fixture_loader()
        b = get_fixture_loader()
        assert a is b

    def test_caching_returns_same_object(self):
        a = self.loader.load("saudi_trends")
        b = self.loader.load("saudi_trends")
        assert a is b
