from __future__ import annotations

import logging
from datetime import datetime

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import (
    PersonaCollaborationCompleted,
    PersonaCollaborationStarted,
)
from sfc.personas.shared.types import PersonaStatus
from sfc.personas.collaboration.models import (
    CollaborationPlan,
    CollaborationRole,
    ConsensusReport,
    PersonaTeam,
)
from sfc.personas.registry.service import PersonaRegistry

logger = logging.getLogger("sfc.personas.collaboration")


class PersonaCollaborationEngine:
    """Manages multi-persona collaboration and consensus building."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self._registry = registry

    async def form_team(
        self, task_type: str, required_capabilities: list[str]
    ) -> PersonaTeam:
        """Select ACTIVE personas matching capabilities and assign roles."""
        all_personas = self._registry.list_all()
        active_personas = [p for p in all_personas if p.status == PersonaStatus.ACTIVE]

        # Select personas with matching capabilities
        matched: list = []
        for p in active_personas:
            if any(cap in p.capabilities for cap in required_capabilities):
                matched.append(p)

        # If no matches, take top 3 by performance
        if not matched:
            matched = sorted(active_personas, key=lambda p: p.performance_score, reverse=True)[:3]

        # Assign roles
        members: list[dict] = []
        for i, persona in enumerate(matched):
            if i == 0:
                role = CollaborationRole.LEAD
            elif i == len(matched) - 1 and len(matched) > 1:
                role = CollaborationRole.REVIEWER
            else:
                role = CollaborationRole.CONTRIBUTOR
            members.append({
                "persona_id": persona.persona_id,
                "role": role,
                "persona_name": persona.name,
            })

        team = PersonaTeam(
            task_type=task_type,
            members=members,
            created_at=datetime.utcnow(),
        )

        get_event_bus().publish(
            PersonaCollaborationStarted(
                event_type="persona_collaboration_started",
                division="personas",
                run_id="",
                payload={
                    "team_id": team.team_id,
                    "task_type": task_type,
                    "member_count": len(members),
                },
            )
        )
        logger.info(
            "[PersonaCollaborationEngine] Formed team %s with %d members for %s",
            team.team_id, len(members), task_type,
        )
        return team

    async def create_plan(self, team: PersonaTeam) -> CollaborationPlan:
        """Build workflow steps from team members."""
        steps: list[dict] = []
        for i, member in enumerate(team.members, start=1):
            action = "lead_execution" if member["role"] == CollaborationRole.LEAD else (
                "review_output" if member["role"] == CollaborationRole.REVIEWER else "contribute"
            )
            steps.append({
                "step": i,
                "persona_id": member["persona_id"],
                "action": action,
                "output": f"output_{member['persona_id'].lower().replace('-', '_')}",
            })

        expected_outputs = [
            "primary_content",
            "reviewed_content",
            "final_approved_output",
        ]

        return CollaborationPlan(
            team=team,
            workflow_steps=steps,
            expected_outputs=expected_outputs,
            created_at=datetime.utcnow(),
        )

    async def build_consensus(self, plan: CollaborationPlan) -> ConsensusReport:
        """Simulate contributions and build consensus."""
        contributions: dict[str, str] = {}
        performance_scores: list[float] = []

        for member in plan.team.members:
            pid = member["persona_id"]
            profile = self._registry.get(pid)
            score = profile.performance_score if profile else 75.0
            performance_scores.append(score)
            contributions[pid] = (
                f"Contribution from {member.get('persona_name', pid)}: "
                f"task={plan.team.task_type}, role={member['role']}, quality={score:.0f}%"
            )

        confidence = (
            sum(performance_scores) / len(performance_scores) / 100.0
            if performance_scores else 0.5
        )

        consensus_output = (
            f"Consensus for {plan.team.task_type}: "
            f"{len(contributions)} persona(s) contributed with {confidence*100:.0f}% confidence."
        )

        get_event_bus().publish(
            PersonaCollaborationCompleted(
                event_type="persona_collaboration_completed",
                division="personas",
                run_id="",
                payload={
                    "plan_id": plan.plan_id,
                    "confidence": confidence,
                    "contributors": len(contributions),
                },
            )
        )
        logger.info(
            "[PersonaCollaborationEngine] Built consensus for plan %s: confidence=%.2f",
            plan.plan_id, confidence,
        )
        return ConsensusReport(
            plan_id=plan.plan_id,
            contributions=contributions,
            consensus_output=consensus_output,
            confidence=confidence,
            generated_at=datetime.utcnow(),
        )

    async def resolve_conflict(
        self, persona_a_id: str, persona_b_id: str, topic: str
    ) -> dict:
        """Resolve conflict between two personas based on performance score."""
        persona_a = self._registry.get(persona_a_id)
        persona_b = self._registry.get(persona_b_id)

        score_a = persona_a.performance_score if persona_a else 0.0
        score_b = persona_b.performance_score if persona_b else 0.0

        if score_a >= score_b:
            winner_id = persona_a_id
            rationale = f"{persona_a_id} wins on topic '{topic}' with higher performance score ({score_a} vs {score_b})"
        else:
            winner_id = persona_b_id
            rationale = f"{persona_b_id} wins on topic '{topic}' with higher performance score ({score_b} vs {score_a})"

        return {
            "resolution": f"Conflict on '{topic}' resolved in favour of {winner_id}",
            "winner_id": winner_id,
            "rationale": rationale,
        }

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaCollaborationEngine",
            "status": "healthy",
            "metrics": {
                "collaboration_roles": len(CollaborationRole),
            },
        }
