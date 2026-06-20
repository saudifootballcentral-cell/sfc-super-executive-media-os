from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import PersonaAssigned
from sfc.personas.shared.types import PersonaCategory, PersonaProfile
from sfc.personas.routing.models import ExecutionPlan, RoutingDecision, RoutingIntent
from sfc.personas.registry.service import PersonaRegistry

logger = logging.getLogger("sfc.personas.routing")

_INTENT_PRIMARY: dict[RoutingIntent, PersonaCategory] = {
    RoutingIntent.CONTENT_CREATION: PersonaCategory.JOURNALISM,
    RoutingIntent.DATA_ANALYSIS: PersonaCategory.ANALYTICS,
    RoutingIntent.GOVERNANCE_REVIEW: PersonaCategory.GOVERNANCE,
    RoutingIntent.REVENUE_OPPORTUNITY: PersonaCategory.REVENUE,
    RoutingIntent.STRATEGIC_PLANNING: PersonaCategory.STRATEGY,
    RoutingIntent.BREAKING_NEWS: PersonaCategory.JOURNALISM,
    RoutingIntent.CAMPAIGN_EXECUTION: PersonaCategory.CREATIVE,
    RoutingIntent.COLLABORATION: PersonaCategory.STRATEGY,
}

# Task-type keyword → RoutingIntent mapping
_TASK_KEYWORDS: list[tuple[list[str], RoutingIntent]] = [
    (["match", "match_report", "report"], RoutingIntent.CONTENT_CREATION),
    (["analytics", "data", "stats", "statistics"], RoutingIntent.DATA_ANALYSIS),
    (["governance", "compliance", "review", "audit"], RoutingIntent.GOVERNANCE_REVIEW),
    (["revenue", "sponsor", "sponsorship", "monetis"], RoutingIntent.REVENUE_OPPORTUNITY),
    (["strategy", "planning", "strategic"], RoutingIntent.STRATEGIC_PLANNING),
    (["breaking", "news", "urgent"], RoutingIntent.BREAKING_NEWS),
    (["campaign"], RoutingIntent.CAMPAIGN_EXECUTION),
]


class PersonaRoutingEngine:
    """Routes tasks to the appropriate personas based on intent."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self._registry = registry

    async def classify_intent(
        self, task_type: str, payload: dict[str, Any] | None = None
    ) -> RoutingIntent:
        """Classify task_type string into a RoutingIntent."""
        task_lower = task_type.lower()
        for keywords, intent in _TASK_KEYWORDS:
            if any(kw in task_lower for kw in keywords):
                return intent
        return RoutingIntent.COLLABORATION

    async def route(
        self, intent: RoutingIntent, available_personas: list[PersonaProfile]
    ) -> RoutingDecision:
        """Select primary and supporting personas for the intent."""
        primary_category = _INTENT_PRIMARY[intent]

        primary_candidates = [
            p for p in available_personas if p.category == primary_category
        ]
        supporting_candidates = [
            p for p in available_personas if p.category != primary_category
        ]

        # Pick highest performer as primary
        primary_candidates.sort(key=lambda p: p.performance_score, reverse=True)
        supporting_candidates.sort(key=lambda p: p.performance_score, reverse=True)

        primary = primary_candidates[0] if primary_candidates else (
            sorted(available_personas, key=lambda p: p.performance_score, reverse=True)[0]
            if available_personas else None
        )

        if primary is None:
            primary_id = "PERSONA-JOURNALIST-01"
            supporting_ids: list[str] = []
            confidence = 0.5
        else:
            primary_id = primary.persona_id
            supporting_ids = [p.persona_id for p in supporting_candidates[:2]]
            confidence = min(1.0, primary.performance_score / 100.0)

        decision = RoutingDecision(
            intent=intent,
            primary_persona_id=primary_id,
            supporting_persona_ids=supporting_ids,
            rationale=f"Selected {primary_id} as primary for {intent.value}; "
                      f"{len(supporting_ids)} supporting persona(s).",
            confidence=confidence,
            decided_at=datetime.utcnow(),
        )

        get_event_bus().publish(
            PersonaAssigned(
                event_type="persona_assigned",
                division="personas",
                run_id="",
                payload={
                    "persona_id": primary_id,
                    "intent": intent.value,
                    "decision_id": decision.decision_id,
                },
            )
        )
        logger.info(
            "[PersonaRoutingEngine] Routed %s → primary=%s, supporting=%s",
            intent.value, primary_id, supporting_ids,
        )
        return decision

    async def build_execution_plan(self, decision: RoutingDecision) -> ExecutionPlan:
        """Build ordered execution steps from routing decision."""
        steps: list[dict] = [
            {
                "step": 1,
                "persona_id": decision.primary_persona_id,
                "action": f"execute_{decision.intent.value}",
            }
        ]
        for i, pid in enumerate(decision.supporting_persona_ids, start=2):
            steps.append(
                {
                    "step": i,
                    "persona_id": pid,
                    "action": f"support_{decision.intent.value}",
                }
            )

        return ExecutionPlan(
            routing_decision=decision,
            steps=steps,
            estimated_duration_ms=500 * len(steps),
            created_at=datetime.utcnow(),
        )

    async def distribute_workload(
        self, persona_ids: list[str], task_count: int
    ) -> dict[str, int]:
        """Evenly distribute tasks across personas (round-robin)."""
        if not persona_ids:
            return {}
        distribution: dict[str, int] = {pid: 0 for pid in persona_ids}
        for i in range(task_count):
            pid = persona_ids[i % len(persona_ids)]
            distribution[pid] += 1
        return distribution

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaRoutingEngine",
            "status": "healthy",
            "metrics": {
                "supported_intents": len(RoutingIntent),
                "task_keyword_rules": len(_TASK_KEYWORDS),
            },
        }
