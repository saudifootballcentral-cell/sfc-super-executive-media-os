from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import PersonaActivated, PersonaDeactivated
from sfc.personas.activation.models import (
    ActivationDecision,
    ActivationPlan,
    ActivationTrigger,
)
from sfc.personas.registry.service import PersonaRegistry

logger = logging.getLogger("sfc.personas.activation")

_TRIGGER_PERSONAS: dict[ActivationTrigger, list[str]] = {
    ActivationTrigger.MATCH_DAY: [
        "PERSONA-JOURNALIST-01",
        "PERSONA-ANALYST-01",
        "PERSONA-CREATIVE-01",
    ],
    ActivationTrigger.BREAKING_NEWS: [
        "PERSONA-JOURNALIST-01",
        "PERSONA-GOVERNANCE-01",
    ],
    ActivationTrigger.TRANSFER_WINDOW: [
        "PERSONA-JOURNALIST-01",
        "PERSONA-REVENUE-01",
        "PERSONA-ANALYST-01",
    ],
    ActivationTrigger.WORLD_CUP: [
        "PERSONA-JOURNALIST-01",
        "PERSONA-ANALYST-01",
        "PERSONA-CREATIVE-01",
        "PERSONA-REVENUE-01",
        "PERSONA-STRATEGIST-01",
    ],
    ActivationTrigger.CAMPAIGN_REQUEST: [
        "PERSONA-CREATIVE-01",
        "PERSONA-REVENUE-01",
        "PERSONA-STRATEGIST-01",
    ],
    ActivationTrigger.CONTENT_REQUEST: [
        "PERSONA-JOURNALIST-01",
        "PERSONA-CREATIVE-01",
    ],
    ActivationTrigger.SPONSOR_OPPORTUNITY: [
        "PERSONA-REVENUE-01",
        "PERSONA-STRATEGIST-01",
    ],
    ActivationTrigger.GROWTH_INITIATIVE: [
        "PERSONA-STRATEGIST-01",
        "PERSONA-ANALYST-01",
    ],
    ActivationTrigger.EXECUTIVE_REQUEST: [
        "PERSONA-STRATEGIST-01",
        "PERSONA-GOVERNANCE-01",
    ],
}

_COST_PER_PERSONA = 0.50


class PersonaActivationEngine:
    """Engine for planning and executing persona activations."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self._registry = registry

    async def plan(
        self, trigger: ActivationTrigger, context: dict[str, Any] | None = None
    ) -> ActivationPlan:
        """Select personas for trigger, detect conflicts, estimate cost."""
        if context is None:
            context = {}
        selected = list(_TRIGGER_PERSONAS.get(trigger, ["PERSONA-JOURNALIST-01"]))

        # Detect conflicts: personas that are not ACTIVE
        conflicts: list[str] = []
        warnings: list[str] = []
        valid_personas: list[str] = []
        for pid in selected:
            profile = self._registry.get(pid)
            if profile is None:
                warnings.append(f"Persona {pid} not found in registry")
            elif profile.status.value != "active":
                conflicts.append(f"Persona {pid} is not active (status={profile.status.value})")
            else:
                valid_personas.append(pid)

        estimated_cost = len(valid_personas) * _COST_PER_PERSONA

        plan = ActivationPlan(
            trigger=trigger,
            selected_personas=selected,
            dependency_order=valid_personas,
            conflicts_detected=conflicts,
            warnings=warnings,
            estimated_cost_usd=estimated_cost,
            created_at=datetime.utcnow(),
        )
        logger.info(
            "[PersonaActivationEngine] Plan %s: trigger=%s, personas=%d, cost=$%.2f",
            plan.plan_id, trigger.value, len(valid_personas), estimated_cost,
        )
        return plan

    async def activate(self, plan: ActivationPlan) -> ActivationDecision:
        """Activate all personas in the plan."""
        activations = []
        for persona_id in plan.dependency_order:
            activation = self._registry.track_activation(
                persona_id=persona_id,
                trigger=plan.trigger.value,
            )
            get_event_bus().publish(
                PersonaActivated(
                    event_type="persona_activated",
                    division="personas",
                    run_id="",
                    payload={
                        "persona_id": persona_id,
                        "trigger": plan.trigger.value,
                        "plan_id": plan.plan_id,
                    },
                )
            )
            activations.append(activation)
            logger.info(
                "[PersonaActivationEngine] Activated persona %s for trigger %s",
                persona_id, plan.trigger.value,
            )

        return ActivationDecision(
            approved=True,
            plan=plan,
            rationale=f"Activated {len(activations)} personas for trigger {plan.trigger.value}",
            activated_personas=activations,
        )

    async def deactivate(self, persona_id: str, run_id: str = "") -> None:
        """Publish PersonaDeactivated event."""
        get_event_bus().publish(
            PersonaDeactivated(
                event_type="persona_deactivated",
                division="personas",
                run_id=run_id,
                payload={"persona_id": persona_id},
            )
        )
        logger.info("[PersonaActivationEngine] Deactivated persona %s", persona_id)

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaActivationEngine",
            "status": "healthy",
            "metrics": {
                "supported_triggers": len(_TRIGGER_PERSONAS),
                "cost_per_persona_usd": _COST_PER_PERSONA,
            },
        }
