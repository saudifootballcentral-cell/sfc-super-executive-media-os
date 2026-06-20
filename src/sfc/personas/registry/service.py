from __future__ import annotations

import logging
from datetime import datetime

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import (
    PersonaRegistered,
    PersonaRetired,
    PersonaUpdated,
)
from sfc.personas.shared.types import (
    PersonaActivation,
    PersonaCategory,
    PersonaProfile,
    PersonaStatus,
)
from sfc.personas.registry.models import PersonaFilter, RegistryReport

logger = logging.getLogger("sfc.personas.registry")


class PersonaRegistry:
    """Central registry for all persona profiles."""

    def __init__(self) -> None:
        self._personas: dict[str, PersonaProfile] = {}
        self._activations: list[PersonaActivation] = []
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Register the 6 built-in seed personas."""
        defaults = [
            PersonaProfile(
                persona_id="PERSONA-JOURNALIST-01",
                name="Saudi Football Journalist",
                category=PersonaCategory.JOURNALISM,
                description="Expert football journalist specialising in Saudi Pro League, transfer news, and match reports.",
                status=PersonaStatus.ACTIVE,
                capabilities=["transfer_reporting", "match_reporting", "breaking_news", "player_interviews"],
                performance_score=85.0,
            ),
            PersonaProfile(
                persona_id="PERSONA-ANALYST-01",
                name="Football Data Analyst",
                category=PersonaCategory.ANALYTICS,
                description="Data analyst providing statistical insights on Saudi Pro League performance.",
                status=PersonaStatus.ACTIVE,
                capabilities=["stats_analysis", "performance_metrics", "predictive_modeling"],
                performance_score=82.0,
            ),
            PersonaProfile(
                persona_id="PERSONA-CREATIVE-01",
                name="Creative Content Director",
                category=PersonaCategory.CREATIVE,
                description="Creative director for visual storytelling, campaign creation, and brand expression.",
                status=PersonaStatus.ACTIVE,
                capabilities=["visual_storytelling", "campaign_creation", "brand_expression"],
                performance_score=80.0,
            ),
            PersonaProfile(
                persona_id="PERSONA-REVENUE-01",
                name="Revenue & Sponsorship Expert",
                category=PersonaCategory.REVENUE,
                description="Revenue strategist identifying sponsorship, partnership, and monetisation opportunities.",
                status=PersonaStatus.ACTIVE,
                capabilities=["sponsor_identification", "deal_structuring", "revenue_optimisation"],
                performance_score=78.0,
            ),
            PersonaProfile(
                persona_id="PERSONA-GOVERNANCE-01",
                name="Compliance & Governance Expert",
                category=PersonaCategory.GOVERNANCE,
                description="Ensures all content meets constitutional requirements, brand safety, and legal compliance.",
                status=PersonaStatus.ACTIVE,
                capabilities=["compliance_review", "brand_safety", "risk_assessment", "fact_checking"],
                performance_score=90.0,
            ),
            PersonaProfile(
                persona_id="PERSONA-STRATEGIST-01",
                name="Strategic Planning Expert",
                category=PersonaCategory.STRATEGY,
                description="Strategic planner aligning content and operations with SFC's annual and quarterly goals.",
                status=PersonaStatus.ACTIVE,
                capabilities=["strategic_planning", "goal_alignment", "opportunity_identification"],
                performance_score=83.0,
            ),
        ]
        for profile in defaults:
            self._personas[profile.persona_id] = profile
        logger.info("[PersonaRegistry] Seeded %d default personas", len(defaults))

    def register(self, profile: PersonaProfile) -> PersonaProfile:
        """Store profile and publish PersonaRegistered event."""
        self._personas[profile.persona_id] = profile
        get_event_bus().publish(
            PersonaRegistered(
                event_type="persona_registered",
                division="personas",
                run_id="",
                payload={"persona_id": profile.persona_id, "name": profile.name},
            )
        )
        logger.info("[PersonaRegistry] Registered persona %s", profile.persona_id)
        return profile

    def get(self, persona_id: str) -> PersonaProfile | None:
        """Retrieve persona by ID."""
        return self._personas.get(persona_id)

    def list_all(self, filter: PersonaFilter | None = None) -> list[PersonaProfile]:
        """Return all personas, optionally filtered."""
        personas = list(self._personas.values())
        if filter is None:
            return personas
        if filter.category is not None:
            personas = [p for p in personas if p.category == filter.category]
        if filter.status is not None:
            personas = [p for p in personas if p.status == filter.status]
        personas = [p for p in personas if p.performance_score >= filter.min_performance_score]
        if filter.capabilities:
            personas = [
                p for p in personas
                if any(cap in p.capabilities for cap in filter.capabilities)
            ]
        return personas

    def update(self, persona_id: str, **kwargs) -> PersonaProfile:
        """Update persona fields and publish PersonaUpdated."""
        profile = self._personas[persona_id]
        data = profile.model_dump()
        data.update(kwargs)
        data["updated_at"] = datetime.utcnow()
        updated = PersonaProfile(**data)
        self._personas[persona_id] = updated
        get_event_bus().publish(
            PersonaUpdated(
                event_type="persona_updated",
                division="personas",
                run_id="",
                payload={"persona_id": persona_id, "updated_fields": list(kwargs.keys())},
            )
        )
        logger.info("[PersonaRegistry] Updated persona %s", persona_id)
        return updated

    def retire(self, persona_id: str) -> PersonaProfile:
        """Set status to RETIRED and publish PersonaRetired."""
        updated = self.update(persona_id, status=PersonaStatus.RETIRED)
        get_event_bus().publish(
            PersonaRetired(
                event_type="persona_retired",
                division="personas",
                run_id="",
                payload={"persona_id": persona_id},
            )
        )
        logger.info("[PersonaRegistry] Retired persona %s", persona_id)
        return updated

    def track_activation(
        self, persona_id: str, trigger: str, context: dict | None = None
    ) -> PersonaActivation:
        """Record activation and increment activation_count."""
        if context is None:
            context = {}
        profile = self._personas.get(persona_id)
        if profile is not None:
            data = profile.model_dump()
            data["activation_count"] = data["activation_count"] + 1
            data["last_used"] = datetime.utcnow()
            data["updated_at"] = datetime.utcnow()
            self._personas[persona_id] = PersonaProfile(**data)

        activation = PersonaActivation(
            persona_id=persona_id,
            trigger=trigger,
            context=context,
        )
        self._activations.append(activation)
        logger.debug("[PersonaRegistry] Tracked activation for %s via %s", persona_id, trigger)
        return activation

    def report(self) -> RegistryReport:
        """Generate registry summary report."""
        personas = list(self._personas.values())
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        total_score = 0.0

        for p in personas:
            by_category[p.category.value] = by_category.get(p.category.value, 0) + 1
            by_status[p.status.value] = by_status.get(p.status.value, 0) + 1
            total_score += p.performance_score

        avg_score = total_score / len(personas) if personas else 0.0

        return RegistryReport(
            total_personas=len(personas),
            by_category=by_category,
            by_status=by_status,
            avg_performance_score=avg_score,
            generated_at=datetime.utcnow(),
        )

    def health_check(self) -> dict:
        """Return health status of the registry."""
        return {
            "component": "PersonaRegistry",
            "status": "healthy",
            "metrics": {
                "total_personas": len(self._personas),
                "total_activations": len(self._activations),
                "active_personas": sum(
                    1 for p in self._personas.values() if p.status == PersonaStatus.ACTIVE
                ),
            },
        }
