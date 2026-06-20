from __future__ import annotations

import logging
from datetime import datetime

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import PersonaRetired, PersonaUpdated
from sfc.personas.shared.types import PersonaLifecycleState, PersonaStatus
from sfc.personas.lifecycle.models import (
    LifecycleReport,
    LifecycleTransition,
    MigrationPlan,
    VersionRecord,
)
from sfc.personas.registry.service import PersonaRegistry

logger = logging.getLogger("sfc.personas.lifecycle")

# Valid state transitions
_NEXT_STATE: dict[PersonaLifecycleState, PersonaLifecycleState] = {
    PersonaLifecycleState.DRAFT: PersonaLifecycleState.TESTING,
    PersonaLifecycleState.TESTING: PersonaLifecycleState.ACTIVE,
    PersonaLifecycleState.ACTIVE: PersonaLifecycleState.DEPRECATED,
    PersonaLifecycleState.DEPRECATED: PersonaLifecycleState.RETIRED,
}

_PREV_STATE: dict[PersonaLifecycleState, PersonaLifecycleState] = {
    PersonaLifecycleState.TESTING: PersonaLifecycleState.DRAFT,
    PersonaLifecycleState.ACTIVE: PersonaLifecycleState.TESTING,
    PersonaLifecycleState.DEPRECATED: PersonaLifecycleState.ACTIVE,
}

_STATUS_MAP: dict[PersonaLifecycleState, PersonaStatus] = {
    PersonaLifecycleState.DRAFT: PersonaStatus.DRAFT,
    PersonaLifecycleState.TESTING: PersonaStatus.TESTING,
    PersonaLifecycleState.ACTIVE: PersonaStatus.ACTIVE,
    PersonaLifecycleState.DEPRECATED: PersonaStatus.DEPRECATED,
    PersonaLifecycleState.RETIRED: PersonaStatus.RETIRED,
}


def _bump_minor_version(version: str) -> str:
    """Bump minor version: 1.0.0 → 1.1.0."""
    parts = version.split(".")
    if len(parts) == 3:
        parts[1] = str(int(parts[1]) + 1)
        parts[2] = "0"
        return ".".join(parts)
    return version


class PersonaLifecycleManager:
    """Manages persona lifecycle transitions."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self._registry = registry
        self._transitions: list[LifecycleTransition] = []

    def _current_lifecycle_state(self, persona_id: str) -> PersonaLifecycleState:
        """Get current lifecycle state from persona status."""
        profile = self._registry.get(persona_id)
        if profile is None:
            return PersonaLifecycleState.DRAFT
        return PersonaLifecycleState(profile.status.value)

    async def promote(self, persona_id: str, reason: str = "") -> LifecycleTransition:
        """Advance persona to next lifecycle state."""
        from_state = self._current_lifecycle_state(persona_id)
        if from_state not in _NEXT_STATE:
            raise ValueError(f"Cannot promote from state {from_state.value}")

        to_state = _NEXT_STATE[from_state]
        new_status = _STATUS_MAP[to_state]
        self._registry.update(persona_id, status=new_status)

        transition = LifecycleTransition(
            persona_id=persona_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason or f"Promoted from {from_state.value} to {to_state.value}",
        )
        self._transitions.append(transition)
        logger.info(
            "[PersonaLifecycleManager] Promoted %s: %s → %s",
            persona_id, from_state.value, to_state.value,
        )
        return transition

    async def demote(self, persona_id: str, reason: str = "") -> LifecycleTransition:
        """Move persona back one lifecycle state."""
        from_state = self._current_lifecycle_state(persona_id)
        if from_state not in _PREV_STATE:
            raise ValueError(f"Cannot demote from state {from_state.value}")

        to_state = _PREV_STATE[from_state]
        new_status = _STATUS_MAP[to_state]
        self._registry.update(persona_id, status=new_status)

        transition = LifecycleTransition(
            persona_id=persona_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason or f"Demoted from {from_state.value} to {to_state.value}",
        )
        self._transitions.append(transition)
        logger.info(
            "[PersonaLifecycleManager] Demoted %s: %s → %s",
            persona_id, from_state.value, to_state.value,
        )
        return transition

    async def retire(self, persona_id: str, reason: str = "") -> LifecycleTransition:
        """Force persona to RETIRED state."""
        from_state = self._current_lifecycle_state(persona_id)
        self._registry.update(persona_id, status=PersonaStatus.RETIRED)

        get_event_bus().publish(
            PersonaRetired(
                event_type="persona_retired",
                division="personas",
                run_id="",
                payload={"persona_id": persona_id, "reason": reason},
            )
        )

        transition = LifecycleTransition(
            persona_id=persona_id,
            from_state=from_state,
            to_state=PersonaLifecycleState.RETIRED,
            reason=reason or "Forced retirement",
        )
        self._transitions.append(transition)
        logger.info("[PersonaLifecycleManager] Retired %s", persona_id)
        return transition

    async def create_version(self, persona_id: str, changes: list[str]) -> VersionRecord:
        """Bump minor version and publish PersonaUpdated."""
        profile = self._registry.get(persona_id)
        current_version = profile.version if profile else "1.0.0"
        new_version = _bump_minor_version(current_version)
        self._registry.update(persona_id, version=new_version)

        get_event_bus().publish(
            PersonaUpdated(
                event_type="persona_updated",
                division="personas",
                run_id="",
                payload={
                    "persona_id": persona_id,
                    "new_version": new_version,
                    "changes": changes,
                },
            )
        )

        record = VersionRecord(
            persona_id=persona_id,
            version=new_version,
            changes=changes,
        )
        logger.info("[PersonaLifecycleManager] Created version %s for %s", new_version, persona_id)
        return record

    async def plan_migration(self, from_id: str, to_id: str) -> MigrationPlan:
        """Create migration steps from one persona to another."""
        steps = [
            f"1. Export knowledge and memory from {from_id}",
            f"2. Validate {to_id} capabilities against {from_id} requirements",
            f"3. Transfer context package to {to_id}",
            f"4. Run parallel testing with both {from_id} and {to_id}",
            f"5. Switch traffic to {to_id}",
            f"6. Retire {from_id} after validation period",
        ]
        return MigrationPlan(
            from_persona_id=from_id,
            to_persona_id=to_id,
            steps=steps,
            estimated_duration_hours=2,
        )

    async def report(self, period: str = "session") -> LifecycleReport:
        """Generate lifecycle report."""
        all_personas = self._registry.list_all()
        active_count = sum(1 for p in all_personas if p.status == PersonaStatus.ACTIVE)
        deprecated_count = sum(1 for p in all_personas if p.status == PersonaStatus.DEPRECATED)
        retired_count = sum(1 for p in all_personas if p.status == PersonaStatus.RETIRED)

        return LifecycleReport(
            period=period,
            transitions=list(self._transitions),
            active_count=active_count,
            deprecated_count=deprecated_count,
            retired_count=retired_count,
            generated_at=datetime.utcnow(),
        )

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaLifecycleManager",
            "status": "healthy",
            "metrics": {
                "total_transitions": len(self._transitions),
            },
        }
