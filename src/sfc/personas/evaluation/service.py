from __future__ import annotations

import logging
import random
from datetime import datetime

from sfc.events.bus import get_event_bus
from sfc.personas.shared.events import PersonaEvaluated
from sfc.personas.shared.types import PersonaMetrics, PersonaProfile
from sfc.personas.evaluation.models import (
    EvaluationCriteria,
    PerformanceReport,
    PersonaScorecard,
)

logger = logging.getLogger("sfc.personas.evaluation")


def _assign_grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


class PersonaEvaluationFramework:
    """Evaluates personas against weighted criteria."""

    def __init__(self, criteria: EvaluationCriteria | None = None) -> None:
        self._criteria = criteria or EvaluationCriteria()

    async def evaluate(
        self, persona: PersonaProfile, metrics: PersonaMetrics
    ) -> PersonaScorecard:
        """Compute weighted score and build scorecard."""
        c = self._criteria
        weighted_score = (
            metrics.accuracy_score * c.accuracy_weight
            + metrics.relevance_score * c.relevance_weight
            + metrics.quality_score * c.quality_weight
            + metrics.efficiency_score * c.efficiency_weight
            + metrics.engagement_impact * c.engagement_weight
        )
        overall_score = min(100.0, max(0.0, weighted_score))
        grade = _assign_grade(overall_score)

        sub_scores = {
            "accuracy": metrics.accuracy_score,
            "relevance": metrics.relevance_score,
            "quality": metrics.quality_score,
            "efficiency": metrics.efficiency_score,
            "engagement": metrics.engagement_impact,
        }
        strengths = [k for k, v in sub_scores.items() if v > 80]
        improvement_areas = [k for k, v in sub_scores.items() if v < 60]

        scorecard = PersonaScorecard(
            persona_id=persona.persona_id,
            metrics=metrics,
            overall_score=overall_score,
            grade=grade,
            improvement_areas=improvement_areas,
            strengths=strengths,
            evaluated_at=datetime.utcnow(),
        )

        get_event_bus().publish(
            PersonaEvaluated(
                event_type="persona_evaluated",
                division="personas",
                run_id="",
                payload={
                    "persona_id": persona.persona_id,
                    "overall_score": overall_score,
                    "grade": grade,
                },
            )
        )
        logger.info(
            "[PersonaEvaluationFramework] Evaluated %s: score=%.1f grade=%s",
            persona.persona_id, overall_score, grade,
        )
        return scorecard

    def _synthetic_metrics(self, persona: PersonaProfile) -> PersonaMetrics:
        """Generate synthetic metrics from performance_score with seeded random variation."""
        random.seed(hash(persona.persona_id) % 10000)
        base = persona.performance_score

        def jitter() -> float:
            return max(0.0, min(100.0, base + random.uniform(-10, 10)))

        return PersonaMetrics(
            persona_id=persona.persona_id,
            accuracy_score=jitter(),
            relevance_score=jitter(),
            quality_score=jitter(),
            efficiency_score=jitter(),
            engagement_impact=jitter(),
            revenue_impact=jitter(),
            collaboration_score=jitter(),
        )

    async def batch_evaluate(self, personas: list[PersonaProfile]) -> PerformanceReport:
        """Evaluate all personas and produce a performance report."""
        scorecards: list[PersonaScorecard] = []
        for persona in personas:
            metrics = self._synthetic_metrics(persona)
            sc = await self.evaluate(persona, metrics)
            scorecards.append(sc)

        top_sc = max(scorecards, key=lambda s: s.overall_score) if scorecards else None
        top_performer_id = top_sc.persona_id if top_sc else None

        retirement_candidates = [
            sc.persona_id for sc in scorecards if sc.overall_score < 40
        ]

        recommendations = [
            "Focus on low-performing personas for targeted improvement.",
            "Increase activation frequency for top performers.",
            "Review retirement candidates with lifecycle manager.",
        ]

        return PerformanceReport(
            period="session",
            scorecards=scorecards,
            top_performer_id=top_performer_id,
            recommendations=recommendations,
            retirement_candidates=retirement_candidates,
            generated_at=datetime.utcnow(),
        )

    async def get_improvement_recommendations(
        self, scorecard: PersonaScorecard
    ) -> list[str]:
        """Return targeted improvement recommendations."""
        recs: list[str] = []
        for area in scorecard.improvement_areas:
            recs.append(f"Improve {area} score through targeted training.")
        if not recs:
            recs.append("Maintain current performance levels.")
        return recs

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaEvaluationFramework",
            "status": "healthy",
            "metrics": {
                "criteria_weights": {
                    "accuracy": self._criteria.accuracy_weight,
                    "relevance": self._criteria.relevance_weight,
                    "quality": self._criteria.quality_weight,
                    "efficiency": self._criteria.efficiency_weight,
                    "engagement": self._criteria.engagement_weight,
                }
            },
        }
