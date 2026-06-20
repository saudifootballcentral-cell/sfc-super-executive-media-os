from __future__ import annotations

import logging
from datetime import datetime

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import PersonaRecommended
from sfc.personas.shared.types import PersonaCategory, PersonaStatus
from sfc.personas.recommendation.models import PersonaRecommendation, RecommendationRequest
from sfc.personas.registry.service import PersonaRegistry

logger = logging.getLogger("sfc.personas.recommendation")

# War room type → preferred categories
_WAR_ROOM_CATEGORIES: dict[str, list[PersonaCategory]] = {
    "match_day": [PersonaCategory.JOURNALISM, PersonaCategory.ANALYTICS],
    "world_cup": [
        PersonaCategory.JOURNALISM,
        PersonaCategory.ANALYTICS,
        PersonaCategory.CREATIVE,
        PersonaCategory.REVENUE,
        PersonaCategory.STRATEGY,
        PersonaCategory.GOVERNANCE,
        PersonaCategory.INTELLIGENCE,
        PersonaCategory.BROADCASTING,
        PersonaCategory.SOCIAL_MEDIA,
        PersonaCategory.SPECIALIST,
    ],
    "transfer": [PersonaCategory.JOURNALISM, PersonaCategory.REVENUE, PersonaCategory.ANALYTICS],
    "crisis": [PersonaCategory.GOVERNANCE, PersonaCategory.JOURNALISM],
    "campaign": [PersonaCategory.CREATIVE, PersonaCategory.REVENUE],
}

# Task type keyword → category bonus
_TASK_CATEGORY_MAP: dict[str, PersonaCategory] = {
    "journalism": PersonaCategory.JOURNALISM,
    "match": PersonaCategory.JOURNALISM,
    "analytics": PersonaCategory.ANALYTICS,
    "data": PersonaCategory.ANALYTICS,
    "creative": PersonaCategory.CREATIVE,
    "campaign": PersonaCategory.CREATIVE,
    "revenue": PersonaCategory.REVENUE,
    "sponsor": PersonaCategory.REVENUE,
    "governance": PersonaCategory.GOVERNANCE,
    "compliance": PersonaCategory.GOVERNANCE,
    "strategy": PersonaCategory.STRATEGY,
    "planning": PersonaCategory.STRATEGY,
    "transfer": PersonaCategory.JOURNALISM,
    "breaking": PersonaCategory.JOURNALISM,
}


class PersonaRecommendationEngine:
    """Recommends personas based on task context."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self._registry = registry

    async def recommend(self, request: RecommendationRequest) -> PersonaRecommendation:
        """Select best personas for the given request."""
        # Get all ACTIVE personas
        all_active = [
            p for p in self._registry.list_all()
            if p.status == PersonaStatus.ACTIVE
        ]

        # Determine preferred categories
        preferred_categories: set[PersonaCategory] = set()

        # From war_room_type
        war_room = request.war_room_type.lower()
        for key, cats in _WAR_ROOM_CATEGORIES.items():
            if key in war_room:
                preferred_categories.update(cats)
                break

        # From task_type keywords
        task_lower = request.task_type.lower()
        for keyword, cat in _TASK_CATEGORY_MAP.items():
            if keyword in task_lower:
                preferred_categories.add(cat)

        # Score each persona
        scored: list[tuple[float, object]] = []
        for p in all_active:
            match_score = 1.0 if p.category in preferred_categories else 0.0
            final_score = (match_score + 0.1) * p.performance_score
            scored.append((final_score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_3 = [p for _, p in scored[:3]]

        recommended_ids = [p.persona_id for p in top_3]
        confidence = (
            sum(p.performance_score for p in top_3) / len(top_3) / 100.0
            if top_3 else 0.5
        )

        expected_impact = {
            "engagement": confidence * 85.0,
            "quality": confidence * 90.0,
            "revenue": confidence * 60.0,
        }

        rationale = (
            f"Recommended {len(top_3)} persona(s) for task '{request.task_type}' "
            f"with confidence {confidence:.2f}. "
            f"Preferred categories: {[c.value for c in preferred_categories] or 'all'}."
        )

        recommendation = PersonaRecommendation(
            request=request,
            recommended_persona_ids=recommended_ids,
            recommended_team=recommended_ids,
            confidence_score=confidence,
            expected_impact=expected_impact,
            rationale=rationale,
            generated_at=datetime.utcnow(),
        )

        get_event_bus().publish(
            PersonaRecommended(
                event_type="persona_recommended",
                division="personas",
                run_id="",
                payload={
                    "recommendation_id": recommendation.recommendation_id,
                    "task_type": request.task_type,
                    "recommended_count": len(recommended_ids),
                    "confidence": confidence,
                },
            )
        )
        logger.info(
            "[PersonaRecommendationEngine] Recommended %d personas for '%s'",
            len(recommended_ids), request.task_type,
        )
        return recommendation

    async def recommend_team(
        self, task_type: str, team_size: int = 3
    ) -> list[str]:
        """Simplified team recommendation returning persona IDs."""
        request = RecommendationRequest(task_type=task_type)
        recommendation = await self.recommend(request)
        return recommendation.recommended_team[:team_size]

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaRecommendationEngine",
            "status": "healthy",
            "metrics": {
                "war_room_mappings": len(_WAR_ROOM_CATEGORIES),
                "task_keyword_mappings": len(_TASK_CATEGORY_MAP),
            },
        }
