"""Data normalisation for Package 10A — unifies fields from all provider types."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sfc.data.confidence import SourceConfidenceScorer
from sfc.data.freshness import DataFreshnessScorer
from sfc.data.models import DataPoint

_confidence = SourceConfidenceScorer()
_freshness = DataFreshnessScorer()


class DataNormalizer:
    """Converts raw provider dicts to DataPoints with scored quality fields."""

    def normalize(self, raw: dict[str, Any], data_source: str) -> DataPoint:
        """Produce a DataPoint with confidence_score and freshness_score populated."""
        collected_at_raw = raw.get("collected_at")
        if isinstance(collected_at_raw, datetime):
            collected_at = collected_at_raw
        elif isinstance(collected_at_raw, str):
            try:
                collected_at = datetime.fromisoformat(collected_at_raw)
            except ValueError:
                collected_at = datetime.utcnow()
        else:
            collected_at = datetime.utcnow()

        point = DataPoint(
            data_source=data_source,
            source_url=raw.get("source_url", raw.get("url", "")),
            collected_at=collected_at,
            confidence_score=_confidence.score(data_source),
            freshness_score=_freshness.score(collected_at),
            # Trend fields
            term=raw.get("term", raw.get("keyword", raw.get("hashtag", ""))),
            tweet_volume=int(raw.get("tweet_volume", raw.get("volume", 0))),
            velocity=float(raw.get("velocity", 0.0)),
            sentiment_label=raw.get("sentiment", raw.get("sentiment_label", "neutral")),
            relevance_score=float(raw.get("relevance_score", 0.0)),
            category=raw.get("category", ""),
            # Sentiment fields
            sentiment_score=float(raw.get("sentiment_score", raw.get("score", 0.0))),
            momentum=float(raw.get("momentum", 0.0)),
            volatility=float(raw.get("volatility", 0.0)),
            sample_size=int(raw.get("sample_size", 0)),
            # Engagement
            views=int(raw.get("views", 0)),
            likes=int(raw.get("likes", 0)),
            shares=int(raw.get("shares", 0)),
            comments_count=int(raw.get("comments", raw.get("comments_count", 0))),
            impressions=int(raw.get("impressions", 0)),
            engagement_rate=float(raw.get("engagement_rate", 0.0)),
            # YouTube-specific
            watch_time_hours=float(raw.get("watch_time_hours", 0.0)),
            avg_view_duration_seconds=float(raw.get("avg_view_duration_seconds", 0.0)),
            avg_view_percentage=float(raw.get("avg_view_percentage", 0.0)),
            subscribers_gained=int(raw.get("subscribers_gained", 0)),
            ctr=float(raw.get("ctr", 0.0)),
            # Influencer
            influence_score=float(raw.get("influence_score", 0.0)),
            trust_score=float(raw.get("trust_score", 0.0)),
            velocity_score=float(raw.get("velocity_score", 0.0)),
            authority_score=float(raw.get("authority_score", 0.0)),
            follower_count=int(raw.get("follower_count", raw.get("followers", 0))),
            # Audience
            segment_size=int(raw.get("segment_size", raw.get("size", 0))),
            growth_rate=float(raw.get("growth_rate", raw.get("growth", 0.0))),
            avg_session_minutes=float(raw.get("avg_session_minutes", 0.0)),
            retention_rate=float(raw.get("retention_rate", 0.0)),
            avg_content_per_day=float(raw.get("avg_content_per_day", 0.0)),
            # Narrative
            strength_score=float(raw.get("strength_score", 0.0)),
            virality_potential=float(raw.get("virality_potential", 0.0)),
            credibility_score=float(raw.get("credibility_score", 0.0)),
            # Virality forecast
            expected_reach=int(raw.get("expected_reach", 0)),
            expected_engagement=int(raw.get("expected_engagement", 0)),
            expected_shares=int(raw.get("expected_shares", 0)),
            expected_views=int(raw.get("expected_views", 0)),
            expected_watch_time_seconds=float(raw.get("expected_watch_time_seconds", 0.0)),
            expected_follower_growth=int(raw.get("expected_follower_growth", 0)),
            # News
            headline=raw.get("headline", raw.get("title", "")),
            summary=raw.get("summary", raw.get("description", "")),
            author=raw.get("author", ""),
            language=raw.get("language", "en"),
            tags=list(raw.get("tags", [])),
            raw=raw,
        )
        return point.compute_hash()

    def normalize_batch(
        self, raws: list[dict[str, Any]], data_source: str
    ) -> list[DataPoint]:
        return [self.normalize(r, data_source) for r in raws]
