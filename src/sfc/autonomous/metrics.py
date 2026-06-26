"""Runtime metrics for the autonomous production loop.

LoopMetrics is updated in place throughout the lifecycle of the scheduler.
Values are read-only outside the loop; no locking needed (single asyncio task).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class LoopMetrics:
    """Counters and timestamps for the autonomous loop."""

    scans_total: int = 0
    pubs_total: int = 0
    pubs_today: int = 0
    cycles_failed: int = 0
    items_deduped: int = 0
    items_governance_rejected: int = 0
    last_scan_at: float = 0.0         # monotonic; 0 = never
    last_publish_at: float = 0.0      # monotonic; 0 = never
    last_cycle_duration_ms: float = 0.0
    last_pub_buffer_id: str = ""
    last_pub_platform: str = ""
    _today_str: str = field(default="", repr=False)

    def record_scan(self) -> None:
        self.scans_total += 1
        self.last_scan_at = time.monotonic()
        today = date.today().isoformat()
        if today != self._today_str:
            self._today_str = today
            self.pubs_today = 0

    def record_publish(self, buffer_id: str = "", platform: str = "") -> None:
        self.pubs_total += 1
        self.pubs_today += 1
        self.last_publish_at = time.monotonic()
        self.last_pub_buffer_id = buffer_id
        self.last_pub_platform = platform

    def record_failure(self) -> None:
        self.cycles_failed += 1

    def to_dict(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            "scans_total": self.scans_total,
            "pubs_total": self.pubs_total,
            "pubs_today": self.pubs_today,
            "cycles_failed": self.cycles_failed,
            "items_deduped": self.items_deduped,
            "items_governance_rejected": self.items_governance_rejected,
            "last_scan_age_s": round(now - self.last_scan_at, 1) if self.last_scan_at else None,
            "last_pub_age_s": round(now - self.last_publish_at, 1) if self.last_publish_at else None,
            "last_cycle_duration_ms": round(self.last_cycle_duration_ms, 1),
            "last_pub_buffer_id": self.last_pub_buffer_id,
            "last_pub_platform": self.last_pub_platform,
        }
