"""Content deduplication for Package 10A."""

from __future__ import annotations

from sfc.data.models import DataPoint


class ContentDeduplicator:
    """Removes duplicate DataPoints using content_hash."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def deduplicate(self, points: list[DataPoint]) -> list[DataPoint]:
        """Return only points with unseen content_hash."""
        unique: list[DataPoint] = []
        for p in points:
            if not p.content_hash:
                p.compute_hash()
            if p.content_hash not in self._seen:
                self._seen.add(p.content_hash)
                unique.append(p)
        return unique

    def reset(self) -> None:
        self._seen.clear()

    @property
    def seen_count(self) -> int:
        return len(self._seen)
