"""OrchestrationStatus — live snapshot of all active and recent runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sfc.orchestration.master_state import MasterState, RunStatus


class RunSummary:
    def __init__(self, state: MasterState) -> None:
        self._s = state

    @property
    def run_id(self) -> str:
        return self._s.run_id

    @property
    def status(self) -> RunStatus:
        return self._s.status

    @property
    def current_stage(self) -> str:
        return self._s.current_stage

    @property
    def is_terminal(self) -> bool:
        return self._s.status in (
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.ABORTED,
        )

    def to_dict(self) -> dict[str, Any]:
        return self._s.to_summary()


class OrchestrationStatus:
    """Registry of all runs in the current process lifetime."""

    def __init__(self) -> None:
        self._active: dict[str, MasterState] = {}
        self._history: list[MasterState] = []

    def register(self, state: MasterState) -> None:
        self._active[state.run_id] = state

    def complete(self, state: MasterState) -> None:
        self._active.pop(state.run_id, None)
        self._history.append(state)

    def get(self, run_id: str) -> MasterState | None:
        return self._active.get(run_id)

    def active_runs(self) -> list[RunSummary]:
        return [RunSummary(s) for s in self._active.values()]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return [s.to_summary() for s in self._history[-limit:]]

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def total_completed(self) -> int:
        return len(self._history)

    def health(self) -> dict[str, Any]:
        terminal_counts: dict[str, int] = {}
        for s in self._history:
            key = s.status.value
            terminal_counts[key] = terminal_counts.get(key, 0) + 1
        return {
            "active_runs": self.active_count,
            "total_completed": self.total_completed,
            "terminal_breakdown": terminal_counts,
            "checked_at": datetime.utcnow().isoformat(),
        }
