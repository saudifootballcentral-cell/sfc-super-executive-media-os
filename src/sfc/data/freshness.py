"""Data freshness scoring for Package 10A."""

from __future__ import annotations

from datetime import datetime, timedelta


class DataFreshnessScorer:
    """Degrades freshness score linearly from 100 → 0 over max_age_hours."""

    def __init__(self, max_age_hours: float = 24.0) -> None:
        self._max_age_seconds = max_age_hours * 3600

    def score(self, collected_at: datetime, now: datetime | None = None) -> float:
        """Return freshness score 0-100. 100 = just collected, 0 = fully stale."""
        if now is None:
            now = datetime.utcnow()
        age_seconds = max((now - collected_at).total_seconds(), 0)
        if age_seconds >= self._max_age_seconds:
            return 0.0
        return round(100.0 * (1.0 - age_seconds / self._max_age_seconds), 2)

    def is_fresh(self, collected_at: datetime, threshold: float = 50.0, now: datetime | None = None) -> bool:
        return self.score(collected_at, now=now) >= threshold

    def ttl_seconds(self, collected_at: datetime, now: datetime | None = None) -> float:
        """Seconds remaining before data is considered fully stale."""
        if now is None:
            now = datetime.utcnow()
        age = max((now - collected_at).total_seconds(), 0)
        return max(self._max_age_seconds - age, 0.0)
