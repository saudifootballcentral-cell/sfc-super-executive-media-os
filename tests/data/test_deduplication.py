"""Deduplication tests — Package 10A."""

from __future__ import annotations

import pytest

from sfc.data.deduplication import ContentDeduplicator
from sfc.data.models import DataPoint


class TestContentDeduplicator:
    def setup_method(self):
        self.dedup = ContentDeduplicator()

    def _make_point(self, term: str, url: str = "") -> DataPoint:
        p = DataPoint(term=term, source_url=url)
        p.compute_hash()
        return p

    def test_single_point_passes_through(self):
        p = self._make_point("AlHilal")
        result = self.dedup.deduplicate([p])
        assert len(result) == 1

    def test_duplicate_points_deduplicated(self):
        p1 = self._make_point("AlHilal")
        p2 = self._make_point("AlHilal")
        result = self.dedup.deduplicate([p1, p2])
        assert len(result) == 1

    def test_different_points_both_kept(self):
        p1 = self._make_point("AlHilal")
        p2 = self._make_point("AlNassr")
        result = self.dedup.deduplicate([p1, p2])
        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        result = self.dedup.deduplicate([])
        assert result == []

    def test_seen_count_increases(self):
        p1 = self._make_point("term1")
        p2 = self._make_point("term2")
        self.dedup.deduplicate([p1, p2])
        assert self.dedup.seen_count == 2

    def test_reset_clears_seen(self):
        p = self._make_point("term1")
        self.dedup.deduplicate([p])
        self.dedup.reset()
        assert self.dedup.seen_count == 0

    def test_after_reset_same_point_passes_again(self):
        p = self._make_point("term1")
        r1 = self.dedup.deduplicate([p])
        self.dedup.reset()
        r2 = self.dedup.deduplicate([self._make_point("term1")])
        assert len(r1) == 1
        assert len(r2) == 1

    def test_point_without_hash_gets_hash_computed(self):
        p = DataPoint(term="nohash")
        result = self.dedup.deduplicate([p])
        assert len(result) == 1
        assert result[0].content_hash != ""

    def test_cross_batch_deduplication(self):
        p1 = self._make_point("spl")
        p2 = self._make_point("spl")
        self.dedup.deduplicate([p1])
        result = self.dedup.deduplicate([p2])
        assert len(result) == 0

    def test_three_duplicates_returns_one(self):
        points = [self._make_point("AlHilal") for _ in range(3)]
        result = self.dedup.deduplicate(points)
        assert len(result) == 1

    def test_five_unique_returns_five(self):
        points = [self._make_point(f"term{i}") for i in range(5)]
        result = self.dedup.deduplicate(points)
        assert len(result) == 5
