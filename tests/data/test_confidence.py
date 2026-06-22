"""Source confidence scorer tests — Package 10A."""

from __future__ import annotations

import pytest

from sfc.data.confidence import SourceConfidenceScorer


class TestSourceConfidenceScorer:
    def setup_method(self):
        self.scorer = SourceConfidenceScorer()

    def test_youtube_api_highest_confidence(self):
        assert self.scorer.score("youtube_api") == 95.0

    def test_x_api_confidence(self):
        assert self.scorer.score("x_api") == 90.0

    def test_google_trends_confidence(self):
        assert self.scorer.score("google_trends") == 85.0

    def test_rss_confidence(self):
        assert self.scorer.score("rss") == 75.0

    def test_csv_import_confidence(self):
        assert self.scorer.score("csv_import") == 70.0

    def test_json_import_confidence(self):
        assert self.scorer.score("json_import") == 70.0

    def test_mock_fixture_confidence(self):
        assert self.scorer.score("mock_fixture") == 60.0

    def test_random_data_zero_confidence(self):
        assert self.scorer.score("random") == 0.0

    def test_unknown_source_returns_default_50(self):
        assert self.scorer.score("totally_unknown_source") == 50.0

    def test_case_insensitive(self):
        assert self.scorer.score("YOUTUBE_API") == 95.0

    def test_score_all_returns_dict(self):
        sources = ["youtube_api", "x_api", "rss"]
        result = self.scorer.score_all(sources)
        assert len(result) == 3
        assert result["youtube_api"] == 95.0
        assert result["x_api"] == 90.0
        assert result["rss"] == 75.0

    def test_known_sources_returns_list(self):
        sources = SourceConfidenceScorer.known_sources()
        assert "youtube_api" in sources
        assert "mock_fixture" in sources
        assert "random" in sources

    def test_real_api_higher_than_fixture(self):
        assert self.scorer.score("youtube_api") > self.scorer.score("mock_fixture")
        assert self.scorer.score("x_api") > self.scorer.score("mock_fixture")

    def test_fixture_higher_than_random(self):
        assert self.scorer.score("mock_fixture") > self.scorer.score("random")

    def test_all_scores_between_0_and_100(self):
        for source in SourceConfidenceScorer.known_sources():
            s = self.scorer.score(source)
            assert 0.0 <= s <= 100.0, f"{source} score {s} out of range"
