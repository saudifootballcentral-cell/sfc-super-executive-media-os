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

    # ------------------------------------------------------------------
    # URL deduplication
    # ------------------------------------------------------------------

    def is_url_seen(self, url: str) -> bool:
        """Dedup by URL (exact match after normalization)."""
        normalized = url.strip().lower().rstrip("/")
        fp = hashlib.sha256(f"url:{normalized}".encode()).hexdigest()
        self._evict()
        return fp in self._store

    def mark_url_seen(self, url: str) -> None:
        """Mark a URL as seen for the dedup window."""
        normalized = url.strip().lower().rstrip("/")
        fp = hashlib.sha256(f"url:{normalized}".encode()).hexdigest()
        self._store[fp] = time.monotonic() + self._window_seconds

    # ------------------------------------------------------------------
    # Content-hash deduplication (detects same story rewritten)
    # ------------------------------------------------------------------

    def is_content_seen(self, content: str) -> bool:
        """Dedup by content hash using first 500 normalized chars."""
        normalized = " ".join(content.strip().lower().split())[:500]
        fp = hashlib.sha256(f"content:{normalized}".encode()).hexdigest()
        self._evict()
        return fp in self._store

    def mark_content_seen(self, content: str) -> None:
        """Mark content as seen for the dedup window."""
        normalized = " ".join(content.strip().lower().split())[:500]
        fp = hashlib.sha256(f"content:{normalized}".encode()).hexdigest()
        self._store[fp] = time.monotonic() + self._window_seconds

    # ------------------------------------------------------------------
    # Platform-level deduplication (headline + platform combination)
    # ------------------------------------------------------------------

    def is_platform_seen(self, headline: str, platform: str) -> bool:
        """Dedup by headline + platform combination."""
        combined = f"platform:{platform}:{headline.strip().lower()}"
        fp = hashlib.sha256(combined.encode()).hexdigest()
        self._evict()
        return fp in self._store

    def mark_platform_seen(self, headline: str, platform: str) -> None:
        """Mark a headline+platform pair as seen for the dedup window."""
        combined = f"platform:{platform}:{headline.strip().lower()}"
        fp = hashlib.sha256(combined.encode()).hexdigest()
        self._store[fp] = time.monotonic() + self._window_seconds
