"""Social War Room Service — activates and manages crisis response."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.social.war_room.models import (
    SocialWarRoomReport,
    SocialWarRoomState,
    SocialWarRoomTrigger,
    WarRoomPriority,
    WarRoomStatus,
)

logger = logging.getLogger("sfc.social.war_room")

_singleton: "SocialWarRoomService | None" = None


def get_war_room_service() -> "SocialWarRoomService":
    global _singleton
    if _singleton is None:
        _singleton = SocialWarRoomService()
    return _singleton


class SocialWarRoomService:
    """Activates and manages social media war room crisis responses."""

    def __init__(self) -> None:
        self._gateway = None
        self._active_rooms: dict[str, SocialWarRoomState] = {}
        self._history: list[SocialWarRoomReport] = []
        self._max_history = 200

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def activate(
        self,
        trigger: SocialWarRoomTrigger,
        context: dict[str, Any] | None = None,
        priority: WarRoomPriority | None = None,
    ) -> SocialWarRoomState:
        """Activate a social war room for the given trigger."""
        if priority is None:
            priority = self._determine_priority(trigger)

        state = SocialWarRoomState(
            trigger=trigger,
            priority=priority,
            status=WarRoomStatus.ACTIVE,
            context=context or {},
            assigned_personas=self._assign_personas(trigger, priority),
        )

        self._active_rooms[state.war_room_id] = state
        logger.warning(
            "[SocialWarRoom] Activated %s | trigger=%s priority=%s",
            state.war_room_id,
            trigger.value,
            priority.value,
        )
        return state

    async def evaluate(
        self,
        trigger: SocialWarRoomTrigger,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Evaluate whether a war room should be activated for the given trigger."""
        context = context or {}
        sentiment_score = context.get("sentiment_score", 0)
        velocity = context.get("velocity", 0)

        critical_triggers = {
            SocialWarRoomTrigger.SENTIMENT_CRISIS,
            SocialWarRoomTrigger.NATIONAL_TEAM_CRISIS,
            SocialWarRoomTrigger.MEDIA_ATTACK,
        }
        if trigger in critical_triggers:
            return True
        if velocity > 7.0:
            return True
        if sentiment_score < -50:
            return True
        return trigger == SocialWarRoomTrigger.BREAKING_STORY and velocity > 5.0

    async def generate_report(
        self,
        war_room_state: SocialWarRoomState,
    ) -> SocialWarRoomReport:
        """Generate a comprehensive war room response report."""
        recommended_responses = await self._get_recommended_responses(war_room_state)
        narrative_strategies = self._get_narrative_strategies(war_room_state.trigger)
        executive_alerts = self._get_executive_alerts(war_room_state)
        persona_assignments = {
            persona: self._get_persona_role(persona, war_room_state.trigger)
            for persona in war_room_state.assigned_personas
        }

        context_summary = (
            f"{war_room_state.trigger.value.replace('_', ' ').title()} — "
            f"Priority {war_room_state.priority.value} war room activated. "
            f"Context: {str(war_room_state.context)[:200]}"
        )

        report = SocialWarRoomReport(
            war_room_id=war_room_state.war_room_id,
            trigger=war_room_state.trigger,
            priority=war_room_state.priority,
            status=war_room_state.status,
            context_summary=context_summary,
            recommended_responses=recommended_responses,
            narrative_strategies=narrative_strategies,
            executive_alerts=executive_alerts,
            persona_assignments=persona_assignments,
            activated_at=war_room_state.activated_at,
            resolved_at=war_room_state.resolved_at,
        )

        if len(self._history) < self._max_history:
            self._history.append(report)

        return report

    async def resolve(self, war_room_id: str) -> bool:
        """Mark a war room as resolved."""
        if war_room_id not in self._active_rooms:
            return False
        state = self._active_rooms[war_room_id]
        state.status = WarRoomStatus.RESOLVED
        state.resolved_at = datetime.utcnow()
        logger.info("[SocialWarRoom] Resolved %s", war_room_id)
        return True

    def get_active_rooms(self) -> list[dict[str, Any]]:
        return [
            {
                "war_room_id": s.war_room_id,
                "trigger": s.trigger.value,
                "priority": s.priority.value,
                "status": s.status.value,
                "activated_at": s.activated_at.isoformat(),
            }
            for s in self._active_rooms.values()
            if s.status != WarRoomStatus.RESOLVED
        ]

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def _determine_priority(self, trigger: SocialWarRoomTrigger) -> WarRoomPriority:
        p1_triggers = {
            SocialWarRoomTrigger.SENTIMENT_CRISIS,
            SocialWarRoomTrigger.NATIONAL_TEAM_CRISIS,
            SocialWarRoomTrigger.MEDIA_ATTACK,
        }
        p2_triggers = {
            SocialWarRoomTrigger.BREAKING_STORY,
            SocialWarRoomTrigger.NARRATIVE_SPIKE,
        }
        if trigger in p1_triggers:
            return WarRoomPriority.P1
        if trigger in p2_triggers:
            return WarRoomPriority.P2
        return WarRoomPriority.P3

    def _assign_personas(
        self, trigger: SocialWarRoomTrigger, priority: WarRoomPriority
    ) -> list[str]:
        base = ["crisis_director", "social_commander"]
        if priority == WarRoomPriority.P1:
            base.extend(["executive_editor", "sentiment_analyst", "media_liaison"])
        elif priority == WarRoomPriority.P2:
            base.extend(["content_coordinator", "narrative_specialist"])
        if trigger == SocialWarRoomTrigger.TRANSFER_EXPLOSION:
            base.append("transfer_analyst")
        if trigger == SocialWarRoomTrigger.REFEREE_CONTROVERSY:
            base.append("editorial_compliance")
        return base

    async def _get_recommended_responses(
        self, state: SocialWarRoomState
    ) -> list[str]:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"War room response for {state.trigger.value} — priority {state.priority.value}",
                task_type="crisis_response",
                max_tokens=250,
            )
            resp = await self.gateway.complete(req)
            return [resp.content]
        except Exception:
            return self._default_responses(state.trigger)

    def _default_responses(self, trigger: SocialWarRoomTrigger) -> list[str]:
        responses = {
            SocialWarRoomTrigger.SENTIMENT_CRISIS: [
                "Issue immediate statement addressing fan concerns",
                "Deploy empathy-first social content across all platforms",
                "Activate fan engagement protocols",
            ],
            SocialWarRoomTrigger.BREAKING_STORY: [
                "Verify story with minimum 2 independent sources before publishing",
                "Prepare breaking news template across all platforms",
                "Alert editorial team for rapid response",
            ],
            SocialWarRoomTrigger.TRANSFER_EXPLOSION: [
                "Monitor all official club channels for confirmation",
                "Prepare transfer announcement content templates",
                "Coordinate with commercial team for sponsor integration",
            ],
            SocialWarRoomTrigger.MEDIA_ATTACK: [
                "Analyze attack vector and origin",
                "Prepare factual rebuttal with sources",
                "Do not engage directly — counter with positive narrative",
            ],
        }
        return responses.get(trigger, [
            "Activate monitoring protocols",
            "Prepare response team",
            "Await executive approval before publishing",
        ])

    def _get_narrative_strategies(self, trigger: SocialWarRoomTrigger) -> list[str]:
        strategies = [
            "Shift narrative to Saudi football positive achievements",
            "Amplify player and club positive stories",
            "Engage trusted influencer network for counter-narrative",
        ]
        if trigger == SocialWarRoomTrigger.NATIONAL_TEAM_CRISIS:
            strategies.insert(0, "Protect national team image with historical context")
        return strategies

    def _get_executive_alerts(self, state: SocialWarRoomState) -> list[str]:
        alerts = [
            f"WAR ROOM ACTIVATED: {state.trigger.value.upper()} — Priority {state.priority.value}",
        ]
        if state.priority == WarRoomPriority.P1:
            alerts.append("IMMEDIATE EXECUTIVE ATTENTION REQUIRED")
            alerts.append("All publishing halted pending governance review")
        return alerts

    def _get_persona_role(
        self, persona: str, trigger: SocialWarRoomTrigger
    ) -> str:
        roles = {
            "crisis_director": "Coordinate overall response strategy",
            "social_commander": "Execute social media response",
            "executive_editor": "Approve all outgoing content",
            "sentiment_analyst": "Monitor sentiment shifts in real-time",
            "media_liaison": "Handle external media inquiries",
            "content_coordinator": "Prepare and distribute response content",
            "narrative_specialist": "Craft alternative narrative messaging",
            "transfer_analyst": "Verify transfer information accuracy",
            "editorial_compliance": "Ensure constitutional compliance",
        }
        return roles.get(persona, "Support war room operations")
