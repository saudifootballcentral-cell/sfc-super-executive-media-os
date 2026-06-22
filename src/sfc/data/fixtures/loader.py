"""Fixture loader for Package 10A."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("sfc.data.fixtures")

_FIXTURES_DIR = Path(__file__).parent
_CACHE: dict[str, Any] = {}


class FixtureLoader:
    """Loads JSON fixture files from the fixtures/ directory."""

    def load(self, fixture_name: str) -> dict[str, Any]:
        """Load a fixture by name (with or without .json extension)."""
        if not fixture_name.endswith(".json"):
            fixture_name = f"{fixture_name}.json"

        if fixture_name in _CACHE:
            return _CACHE[fixture_name]

        path = _FIXTURES_DIR / fixture_name
        if not path.exists():
            logger.warning("[FixtureLoader] Fixture not found: %s", path)
            return {}

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            _CACHE[fixture_name] = data
            logger.debug("[FixtureLoader] Loaded fixture: %s", fixture_name)
            return data
        except Exception as exc:
            logger.error("[FixtureLoader] Failed to load %s: %s", fixture_name, exc)
            return {}

    def get_trends(self) -> list[dict[str, Any]]:
        return self.load("saudi_trends").get("trends", [])

    def get_topic_scores(self) -> dict[str, Any]:
        return self.load("saudi_trends").get("topic_scores", {})

    def get_sentiment(self, entity: str) -> dict[str, Any]:
        entities = self.load("saudi_sentiment").get("entities", {})
        default = self.load("saudi_sentiment").get("default_sentiment", {})
        return entities.get(entity, default)

    def get_analytics_channel(self) -> dict[str, Any]:
        return self.load("saudi_analytics").get("youtube_channel", {})

    def get_analytics_video(self, video_type: str = "default") -> dict[str, Any]:
        benchmarks = self.load("saudi_analytics").get("youtube_video_benchmarks", {})
        return benchmarks.get(video_type, benchmarks.get("default", {}))

    def get_x_post_metrics(self, post_type: str = "default") -> dict[str, Any]:
        benchmarks = self.load("saudi_analytics").get("x_post_benchmarks", {})
        return benchmarks.get(post_type, benchmarks.get("default", {}))

    def get_influencer_profile(self, handle: str) -> dict[str, Any]:
        profiles = self.load("saudi_analytics").get("influencer_profiles", {})
        return profiles.get(handle, profiles.get("default", {}))

    def get_audience_segment(self, segment_type: str) -> dict[str, Any]:
        segments = self.load("saudi_analytics").get("audience_segments", {})
        return segments.get(segment_type, {})

    def get_news_items(self) -> list[dict[str, Any]]:
        return self.load("saudi_news").get("items", [])


_singleton: FixtureLoader | None = None


def get_fixture_loader() -> FixtureLoader:
    global _singleton
    if _singleton is None:
        _singleton = FixtureLoader()
    return _singleton
