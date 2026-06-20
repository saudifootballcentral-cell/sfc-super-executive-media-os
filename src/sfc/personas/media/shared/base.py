"""Base class for all Media & Platform Personas."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory, PersonaProfile, PersonaStatus
from sfc.personas.media.shared.models import (
    ContentFormat,
    Platform,
    PlatformInsight,
    ViralityScore,
)


class BaseMediaPersona(ABC):
    """Abstract base for all media & platform intelligence personas."""

    PERSONA_ID: str = ""
    PERSONA_NAME: str = ""
    PERSONA_CATEGORY: PersonaCategory = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION: str = ""
    PERSONA_CAPABILITIES: list[str] = []
    PERSONA_PERFORMANCE_SCORE: float = 82.0
    PERSONA_PLATFORM: Platform = Platform.TIKTOK

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"sfc.personas.media.{self.__class__.__name__.lower()}")
        self._insights: list[PlatformInsight] = []

    @property
    def profile(self) -> PersonaProfile:
        return PersonaProfile(
            persona_id=self.PERSONA_ID,
            name=self.PERSONA_NAME,
            category=self.PERSONA_CATEGORY,
            description=self.PERSONA_DESCRIPTION,
            status=PersonaStatus.ACTIVE,
            capabilities=list(self.PERSONA_CAPABILITIES),
            performance_score=self.PERSONA_PERFORMANCE_SCORE,
            metadata={"domain": "media_platform"},
        )

    @abstractmethod
    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        """Generate a platform-specific insight from context."""
        ...

    @abstractmethod
    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Perform platform-specific analysis."""
        ...

    def _build_insight(
        self,
        context: dict[str, Any],
        content_format: ContentFormat,
        title: str,
        summary: str,
        hook: str,
        recommendations: list[str],
        optimization_tips: list[str],
        virality_score: float = 70.0,
        predicted_reach: int = 50000,
        predicted_engagement_rate: float = 4.5,
        predicted_ctr: float = 3.2,
        tags: list[str] | None = None,
    ) -> PlatformInsight:
        level = (
            ViralityScore.VIRAL if virality_score >= 85
            else ViralityScore.HIGH if virality_score >= 70
            else ViralityScore.MEDIUM if virality_score >= 50
            else ViralityScore.LOW
        )
        insight = PlatformInsight(
            persona_id=self.PERSONA_ID,
            persona_name=self.PERSONA_NAME,
            platform=self.PERSONA_PLATFORM,
            content_format=content_format,
            title=title,
            summary=summary,
            hook=hook,
            key_recommendations=recommendations,
            optimization_tips=optimization_tips,
            predicted_reach=predicted_reach,
            predicted_engagement_rate=predicted_engagement_rate,
            predicted_ctr=predicted_ctr,
            virality_score=virality_score,
            virality_level=level,
            tags=tags or [],
        )
        self._insights.append(insight)
        return insight

    def get_insights(self) -> list[PlatformInsight]:
        return list(self._insights)

    def health_check(self) -> dict[str, Any]:
        return {
            "component": self.__class__.__name__,
            "persona_id": self.PERSONA_ID,
            "status": "healthy",
            "platform": self.PERSONA_PLATFORM,
            "insights_generated": len(self._insights),
        }
