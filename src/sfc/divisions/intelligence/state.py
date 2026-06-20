"""Intelligence Division — state manager backed by WorkingMemory."""

from __future__ import annotations

from typing import Any

from sfc.divisions.intelligence.models import IntelligenceState
from sfc.memory.working_memory import WorkingMemory


class DivisionStateManager:
    """Manages the Intelligence division's in-flight state."""

    def __init__(self) -> None:
        self._working = WorkingMemory()
        self._state = IntelligenceState()

    def get_state(self) -> IntelligenceState:
        return self._state.model_copy()

    def update_state(self, **kwargs: Any) -> None:
        updated = self._state.model_dump()
        updated.update(kwargs)
        self._state = IntelligenceState(**updated)

    def reset(self) -> None:
        self._state = IntelligenceState()
