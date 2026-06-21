"""Scheduler persistence — in-memory store with optional JSON file export."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.scheduler.jobs import JobDefinition, JobRecord

logger = logging.getLogger("sfc.scheduler.persistence")


class SchedulerPersistence:
    """In-memory job store with optional file-based snapshot."""

    def __init__(self, snapshot_path: str | None = None) -> None:
        self._snapshot_path: Path | None = Path(snapshot_path) if snapshot_path else None
        self._jobs: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []

    def save_job(self, job: JobDefinition) -> None:
        self._jobs[job.job_id] = job.model_dump(mode="json")

    def delete_job(self, job_id: str) -> bool:
        return bool(self._jobs.pop(job_id, None))

    def load_jobs(self) -> list[JobDefinition]:
        return [JobDefinition(**d) for d in self._jobs.values()]

    def save_record(self, record: JobRecord) -> None:
        self._history.append(record.model_dump(mode="json"))
        # Keep last 5000 records in memory
        if len(self._history) > 5000:
            self._history = self._history[-5000:]

    def load_records(self) -> list[JobRecord]:
        return [JobRecord(**d) for d in self._history]

    def export_snapshot(self) -> dict[str, Any]:
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "jobs": list(self._jobs.values()),
            "history_count": len(self._history),
            "recent_history": self._history[-100:],
        }

    def write_snapshot_file(self) -> bool:
        if self._snapshot_path is None:
            return False
        try:
            self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot = self.export_snapshot()
            self._snapshot_path.write_text(json.dumps(snapshot, indent=2, default=str))
            logger.debug("[Persistence] Snapshot written to %s", self._snapshot_path)
            return True
        except Exception as exc:
            logger.warning("[Persistence] Snapshot write failed: %s", exc)
            return False

    def load_snapshot_file(self) -> bool:
        if self._snapshot_path is None or not self._snapshot_path.exists():
            return False
        try:
            data = json.loads(self._snapshot_path.read_text())
            self._jobs = {j["job_id"]: j for j in data.get("jobs", [])}
            self._history = data.get("recent_history", [])
            logger.info("[Persistence] Loaded snapshot: %d jobs", len(self._jobs))
            return True
        except Exception as exc:
            logger.warning("[Persistence] Snapshot load failed: %s", exc)
            return False
