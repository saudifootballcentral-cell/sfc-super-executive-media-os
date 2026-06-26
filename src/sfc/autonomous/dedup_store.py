"""In-memory TTL deduplication store for autonomous loop content fingerprints.

Keys are SHA-256 hashes of normalized headlines.
Window length is controlled by the DEDUP_WINDOW_HOURS env var (default: 24h).
Entries are lazily evicted on the next read.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time

logger = logging.getLogger("sfc.autonomous.dedup_store")


class DedupStore:
    """TTL-based deduplication store for news-item headlines."""

    def __init__(self, window_hours: float | None = None) -> None:
        if window_hours is None:
            window_hours = float(os.environ.get("DEDUP_WINDOW_HOURS", "24"))
        self._window_seconds = window_hours * 3600.0
        # fingerprint → monotonic expiry timestamp
        self._store: dict[str, float] = {}

    def fingerprint(self, headline: str) -> str:
        """Return stable SHA-256 hex digest of the normalized headline."""
        return hashlib.sha256(headline.strip().lower().encode()).hexdigest()

    def is_seen(self, headline: str) -> bool:
        self._evict()
        return self.fingerprint(headline) in self._store

    def mark_seen(self, headline: str) -> None:
        fp = self.fingerprint(headline)
        self._store[fp] = time.monotonic() + self._window_seconds

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [k for k, exp in self._store.items() if exp <= now]
        for k in expired:
            del self._store[k]

    @property
    def size(self) -> int:
        self._evict()
        return len(self._store)
