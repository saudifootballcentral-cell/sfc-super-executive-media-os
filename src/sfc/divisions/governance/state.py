"""Governance Division — state manager."""

from __future__ import annotations

from typing import Any

from sfc.divisions.governance.models import GovernanceState
from sfc.memory.working_memory import WorkingMemory


class DivisionStateManager:
    def __init__(self) -> None:
        self._working = WorkingMemory()
        self._state = GovernanceState()

    def get_state(self) -> GovernanceState:
        return self._state.model_copy()

    def update_state(self, **kwargs: Any) -> None:
        updated = self._state.model_dump()
        updated.update(kwargs)
        self._state = GovernanceState(**updated)

    def reset(self) -> None:
        self._state = GovernanceState()
