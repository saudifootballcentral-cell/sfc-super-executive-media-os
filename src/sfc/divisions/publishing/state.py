"""Publishing Division — state manager."""

from __future__ import annotations

from typing import Any

from sfc.divisions.publishing.models import PublishingState
from sfc.memory.working_memory import WorkingMemory


class DivisionStateManager:
    def __init__(self) -> None:
        self._working = WorkingMemory()
        self._state = PublishingState()

    def get_state(self) -> PublishingState:
        return self._state.model_copy()

    def update_state(self, **kwargs: Any) -> None:
        updated = self._state.model_dump()
        updated.update(kwargs)
        self._state = PublishingState(**updated)

    def reset(self) -> None:
        self._state = PublishingState()
