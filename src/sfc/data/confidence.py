"""Source confidence scoring for Package 10A."""

from __future__ import annotations

_SOURCE_SCORES: dict[str, float] = {
    "youtube_api": 95.0,
    "x_api": 90.0,
    "google_trends": 85.0,
    "rss": 75.0,
    "csv_import": 70.0,
    "json_import": 70.0,
    "mock_fixture": 60.0,
    "random": 0.0,
}


class SourceConfidenceScorer:
    """Assigns a confidence score (0-100) to a data source."""

    def score(self, data_source: str) -> float:
        return _SOURCE_SCORES.get(data_source.lower(), 50.0)

    def score_all(self, data_sources: list[str]) -> dict[str, float]:
        return {s: self.score(s) for s in data_sources}

    @staticmethod
    def known_sources() -> list[str]:
        return list(_SOURCE_SCORES.keys())
