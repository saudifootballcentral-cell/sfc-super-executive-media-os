"""Base class for all Sports Intelligence Personas."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory, PersonaProfile, PersonaStatus
from sfc.personas.sports.shared.events import PersonaInsightGenerated
from sfc.personas.sports.shared.models import (
    InsightConfidence,
    InsightType,
    PersonaInsight,
    PersonaKnowledgeState,
)


class BaseSportsPersona(ABC):
    """Abstract base class for all sports intelligence personas."""

    # Subclasses must set these class attributes
    PERSONA_ID: str = ""
    PERSONA_NAME: str = ""
    PERSONA_CATEGORY: PersonaCategory = PersonaCategory.SPECIALIST
    PERSONA_DESCRIPTION: str = ""
    PERSONA_CAPABILITIES: list[str] = []
    PERSONA_PERFORMANCE_SCORE: float = 82.0

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"sfc.personas.sports.{self.__class__.__name__.lower()}")
        self._insights: list[PersonaInsight] = []
        self._knowledge_state = PersonaKnowledgeState(
            persona_id=self.PERSONA_ID,
            domain=self.PERSONA_NAME,
        )

    @property
    def profile(self) -> PersonaProfile:
        """Return a PersonaProfile for registration in the registry."""
        return PersonaProfile(
            persona_id=self.PERSONA_ID,
            name=self.PERSONA_NAME,
            category=self.PERSONA_CATEGORY,
            description=self.PERSONA_DESCRIPTION,
            status=PersonaStatus.ACTIVE,
            capabilities=list(self.PERSONA_CAPABILITIES),
            performance_score=self.PERSONA_PERFORMANCE_SCORE,
            metadata={"domain": "sports_intelligence"},
        )

    @abstractmethod
    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        """Generate a domain-specific insight from context."""
        ...

    @abstractmethod
    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Perform domain-specific analysis."""
        ...

    def _build_insight(
        self,
        context: dict[str, Any],
        insight_type: InsightType,
        title: str,
        summary: str,
        key_findings: list[str],
        recommendations: list[str],
        confidence_score: float = 82.0,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> PersonaInsight:
        """Build and store an insight, then publish PersonaInsightGenerated."""
        level = (
            InsightConfidence.HIGH if confidence_score >= 85
            else InsightConfidence.MEDIUM if confidence_score >= 65
            else InsightConfidence.LOW
        )
        insight = PersonaInsight(
            persona_id=self.PERSONA_ID,
            persona_name=self.PERSONA_NAME,
            insight_type=insight_type,
            title=title,
            summary=summary,
            key_findings=key_findings,
            recommendations=recommendations,
            confidence_score=confidence_score,
            confidence_level=level,
            tags=tags or [],
            entities_mentioned=entities or [],
        )
        self._insights.append(insight)
        get_event_bus().publish(PersonaInsightGenerated(
            division="personas",
            run_id=context.get("run_id", ""),
            payload={
                "insight_id": insight.insight_id,
                "persona_id": self.PERSONA_ID,
                "title": title,
            },
        ))
        return insight

    def get_insights(self) -> list[PersonaInsight]:
        """Return all generated insights."""
        return list(self._insights)

    def health_check(self) -> dict[str, Any]:
        """Return health status of this persona."""
        return {
            "component": self.__class__.__name__,
            "persona_id": self.PERSONA_ID,
            "status": "healthy",
            "insights_generated": len(self._insights),
        }
