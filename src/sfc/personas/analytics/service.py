from __future__ import annotations

import logging
from datetime import datetime

from sfc.personas.shared.types import PersonaStatus
from sfc.personas.analytics.models import (
    AnalyticsPeriod,
    OptimizationRecommendation,
    PerformanceDashboard,
    PersonaRanking,
)
from sfc.personas.registry.service import PersonaRegistry

logger = logging.getLogger("sfc.personas.analytics")


class PersonaPerformanceAnalytics:
    """Performance analytics and dashboard for personas."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self._registry = registry

    async def rank_personas(self) -> list[PersonaRanking]:
        """Sort all ACTIVE personas by performance_score desc."""
        active = [
            p for p in self._registry.list_all()
            if p.status == PersonaStatus.ACTIVE
        ]
        active.sort(key=lambda p: p.performance_score, reverse=True)
        return [
            PersonaRanking(
                rank=i + 1,
                persona_id=p.persona_id,
                persona_name=p.name,
                overall_score=p.performance_score,
                category=p.category,
                trend="stable",
            )
            for i, p in enumerate(active)
        ]

    async def build_dashboard(
        self, period: AnalyticsPeriod = AnalyticsPeriod.SESSION
    ) -> PerformanceDashboard:
        """Build analytics dashboard for all personas."""
        all_personas = self._registry.list_all()
        active_personas = [p for p in all_personas if p.status == PersonaStatus.ACTIVE]
        rankings = await self.rank_personas()

        avg_score = (
            sum(p.performance_score for p in active_personas) / len(active_personas)
            if active_personas else 0.0
        )

        top_performer = rankings[0] if rankings else None

        # Category breakdown: avg score per category
        category_scores: dict[str, list[float]] = {}
        for p in active_personas:
            cat = p.category.value
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(p.performance_score)
        category_breakdown = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }

        optimization_recommendations = [
            "Activate underutilised personas to improve coverage.",
            "Focus resources on top-ranked personas for maximum impact.",
            "Review personas with declining performance scores.",
        ]

        return PerformanceDashboard(
            period=period,
            total_personas=len(all_personas),
            active_personas=len(active_personas),
            avg_performance_score=avg_score,
            top_performer=top_performer,
            rankings=rankings,
            category_breakdown=category_breakdown,
            optimization_recommendations=optimization_recommendations,
            generated_at=datetime.utcnow(),
        )

    async def get_optimization_recommendations(
        self, persona_id: str
    ) -> OptimizationRecommendation:
        """Return optimization recommendations for a persona."""
        profile = self._registry.get(persona_id)
        current_score = profile.performance_score if profile else 0.0

        if current_score < 70:
            actions = ["Increase activation frequency", "Expand capability set"]
            target_score = 75.0
            priority = "high"
        elif current_score < 85:
            actions = ["Improve collaboration score"]
            target_score = 88.0
            priority = "medium"
        else:
            actions = ["Maintain current performance"]
            target_score = min(100.0, current_score + 5.0)
            priority = "low"

        return OptimizationRecommendation(
            persona_id=persona_id,
            current_score=current_score,
            target_score=target_score,
            actions=actions,
            priority=priority,
        )

    async def generate_report(
        self, period: AnalyticsPeriod = AnalyticsPeriod.SESSION
    ) -> dict:
        """Generate serializable analytics report."""
        dashboard = await self.build_dashboard(period)
        rankings = await self.rank_personas()

        return {
            "dashboard_id": dashboard.dashboard_id,
            "period": period.value,
            "total_personas": dashboard.total_personas,
            "active_personas": dashboard.active_personas,
            "avg_performance_score": dashboard.avg_performance_score,
            "top_performer_id": dashboard.top_performer.persona_id if dashboard.top_performer else None,
            "rankings_count": len(rankings),
            "category_breakdown": dashboard.category_breakdown,
            "optimization_recommendations": dashboard.optimization_recommendations,
            "generated_at": dashboard.generated_at.isoformat(),
        }

    def health_check(self) -> dict:
        """Return health status."""
        total = len(self._registry.list_all())
        active = sum(
            1 for p in self._registry.list_all() if p.status == PersonaStatus.ACTIVE
        )
        return {
            "component": "PersonaPerformanceAnalytics",
            "status": "healthy",
            "metrics": {
                "total_personas": total,
                "active_personas": active,
            },
        }
