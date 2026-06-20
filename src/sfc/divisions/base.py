"""Base Division interface — all divisions implement this contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.core.models import Division
from sfc.events.types import BaseEvent
from sfc.graph.state import SFCState


# ---------------------------------------------------------------------------
# Shared Pydantic models used across all divisions
# ---------------------------------------------------------------------------


class DivisionInput(BaseModel):
    """Standardised input for any division's execute() call."""

    run_id: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    state_snapshot: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}


class DivisionOutput(BaseModel):
    """Standardised output from any division's execute() call."""

    run_id: str
    division: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    events_to_publish: list[BaseEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0

    model_config = {"arbitrary_types_allowed": True}


class ValidationResult(BaseModel):
    """Result of a division's validate() call."""

    valid: bool
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DivisionReport(BaseModel):
    """Periodic report produced by a division."""

    division: str
    period: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DivisionHealth(BaseModel):
    """Health snapshot for AgentOps monitoring."""

    division: str
    status: str  # "healthy" | "degraded" | "unhealthy"
    last_check: datetime = Field(default_factory=datetime.utcnow)
    metrics: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class DivisionInterface(ABC):
    """Abstract interface that every division must implement.

    All methods receive SFCState (or DivisionInput) and return state update
    dicts or typed output objects. This ensures divisions are swappable
    implementations behind a stable contract.
    """

    division: Division

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def initialize(self) -> None:
        """Set up connections, warm caches, load config. Called once on startup."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Graceful teardown — close connections, flush buffers."""
        ...

    # ------------------------------------------------------------------
    # Primary execution
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(self, input: DivisionInput) -> DivisionOutput:
        """Main stateless execution path.

        Receives a typed DivisionInput, returns a typed DivisionOutput.
        All business logic lives here.
        """
        ...

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    @abstractmethod
    async def handle_event(self, event: BaseEvent) -> None:
        """React to an incoming event from another division."""
        ...

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @abstractmethod
    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        """Validate a content dict according to this division's rules."""
        ...

    # ------------------------------------------------------------------
    # Reporting & health
    # ------------------------------------------------------------------

    @abstractmethod
    async def report(self) -> DivisionReport:
        """Generate and return the division's performance report."""
        ...

    @abstractmethod
    def health_check(self) -> DivisionHealth:
        """Return division health. Must never raise."""
        ...

    # ------------------------------------------------------------------
    # Legacy process() — kept for backwards-compat with graph nodes that
    # still call process(state). New code should call execute().
    # ------------------------------------------------------------------

    async def process(self, state: SFCState) -> dict[str, Any]:
        """Delegate to execute() using the full state as input."""
        inp = DivisionInput(
            run_id=state.get("run_id", ""),
            task_type=state.get("task_type", "news"),
            payload=state.get("task_payload", {}),
            state_snapshot=dict(state),
        )
        out = await self.execute(inp)
        return out.data

    def describe(self) -> str:
        """Return a one-line description of this division's role."""
        return f"{self.division.value} division"
