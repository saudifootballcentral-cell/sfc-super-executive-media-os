"""Base Division interface — all divisions implement this contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sfc.core.models import Division
from sfc.graph.state import SFCState


class DivisionInterface(ABC):
    """Abstract interface that every division must implement.

    All methods receive SFCState (or parts of it) and return state update dicts.
    This ensures divisions are swappable implementations behind a stable contract.
    """

    division: Division

    @abstractmethod
    async def process(self, state: SFCState) -> dict[str, Any]:
        """Main entry point for a division during its pipeline stage."""
        ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return division health status for AgentOps monitoring."""
        ...

    @abstractmethod
    def describe(self) -> str:
        """Return a one-line description of this division's role."""
        ...
