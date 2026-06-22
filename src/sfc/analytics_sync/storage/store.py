"""Persistent storage for analytics records — JSON by default, PostgreSQL if DATABASE_URL is set."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.analytics_sync.aggregation.models import AggregatedPerformance, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.storage")

_DEFAULT_STORAGE_ROOT = Path("./artifacts/analytics_sync")


class AnalyticsStore:
    """Persist and retrieve UnifiedAnalyticsRecords.

    Storage backend:
    - JSON files in _DEFAULT_STORAGE_ROOT (default, zero-dependency)
    - PostgreSQL when DATABASE_URL env var is set (optional, not yet wired)
    """

    def __init__(self, storage_root: Path | None = None) -> None:
        self._root = storage_root or Path(
            os.environ.get("ANALYTICS_STORAGE_PATH", str(_DEFAULT_STORAGE_ROOT))
        )
        self._records_dir = self._root / "records"
        self._agg_dir = self._root / "aggregated"
        self._records_dir.mkdir(parents=True, exist_ok=True)
        self._agg_dir.mkdir(parents=True, exist_ok=True)
        self._db_url = os.environ.get("DATABASE_URL", "")

    # ------------------------------------------------------------------
    # UnifiedAnalyticsRecord
    # ------------------------------------------------------------------

    async def save_record(self, record: UnifiedAnalyticsRecord) -> str:
        """Persist a single analytics record. Returns record_id."""
        path = self._records_dir / f"{record.record_id}.json"
        path.write_text(record.model_dump_json(indent=2))
        logger.debug("[AnalyticsStore] saved record %s (%s)", record.record_id, record.platform.value)
        return record.record_id

    async def get_record(self, record_id: str) -> UnifiedAnalyticsRecord | None:
        path = self._records_dir / f"{record_id}.json"
        if not path.exists():
            return None
        return UnifiedAnalyticsRecord.model_validate_json(path.read_text())

    async def list_records(
        self,
        *,
        platform: str | None = None,
        content_id: str | None = None,
        run_id: str | None = None,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[UnifiedAnalyticsRecord]:
        records: list[UnifiedAnalyticsRecord] = []
        for p in sorted(self._records_dir.glob("*.json"), reverse=True)[:limit * 2]:
            try:
                r = UnifiedAnalyticsRecord.model_validate_json(p.read_text())
                if platform and r.platform.value != platform:
                    continue
                if content_id and r.content_id != content_id:
                    continue
                if run_id and r.run_id != run_id:
                    continue
                if since and r.fetched_at < since:
                    continue
                records.append(r)
                if len(records) >= limit:
                    break
            except Exception as exc:
                logger.warning("[AnalyticsStore] Skipping corrupt record %s: %s", p.name, exc)
        return records

    async def delete_record(self, record_id: str) -> bool:
        path = self._records_dir / f"{record_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # ------------------------------------------------------------------
    # AggregatedPerformance
    # ------------------------------------------------------------------

    async def save_aggregated(self, agg: AggregatedPerformance) -> str:
        path = self._agg_dir / f"{agg.agg_id}.json"
        path.write_text(agg.model_dump_json(indent=2))
        logger.debug("[AnalyticsStore] saved aggregated %s (%s/%s)", agg.agg_id, agg.dimension, agg.period)
        return agg.agg_id

    async def list_aggregated(
        self,
        *,
        dimension: str | None = None,
        period: str | None = None,
        limit: int = 200,
    ) -> list[AggregatedPerformance]:
        results: list[AggregatedPerformance] = []
        for p in sorted(self._agg_dir.glob("*.json"), reverse=True)[:limit * 2]:
            try:
                a = AggregatedPerformance.model_validate_json(p.read_text())
                if dimension and a.dimension != dimension:
                    continue
                if period and a.period != period:
                    continue
                results.append(a)
                if len(results) >= limit:
                    break
            except Exception as exc:
                logger.warning("[AnalyticsStore] Skipping corrupt agg %s: %s", p.name, exc)
        return results

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    async def get_stats(self) -> dict[str, Any]:
        records = list(self._records_dir.glob("*.json"))
        aggs = list(self._agg_dir.glob("*.json"))
        return {
            "total_records": len(records),
            "total_aggregated": len(aggs),
            "storage_root": str(self._root),
            "backend": "postgresql" if self._db_url else "json",
        }


_singleton: AnalyticsStore | None = None


def get_analytics_store() -> AnalyticsStore:
    global _singleton
    if _singleton is None:
        _singleton = AnalyticsStore()
    return _singleton
