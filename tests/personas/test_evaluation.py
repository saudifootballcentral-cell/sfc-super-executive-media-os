"""Tests for PersonaEvaluationFramework."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.evaluation.service import PersonaEvaluationFramework
from sfc.personas.evaluation.models import EvaluationCriteria
from sfc.personas.shared.types import PersonaCategory, PersonaMetrics, PersonaProfile, PersonaStatus


def _make_metrics(persona_id: str, score: float) -> PersonaMetrics:
    return PersonaMetrics(
        persona_id=persona_id,
        accuracy_score=score,
        relevance_score=score,
        quality_score=score,
        efficiency_score=score,
        engagement_impact=score,
    )


class TestPersonaEvaluationFramework:
    def setup_method(self):
        get_event_bus().reset()

    async def test_evaluate_active_persona(self):
        registry = PersonaRegistry()
        evaluator = PersonaEvaluationFramework()
        persona = registry.get("PERSONA-GOVERNANCE-01")
        metrics = _make_metrics("PERSONA-GOVERNANCE-01", 90.0)
        scorecard = await evaluator.evaluate(persona, metrics)
        assert scorecard.grade in ("A", "B", "C", "D", "F")
        assert 0 <= scorecard.overall_score <= 100

    async def test_grade_thresholds(self):
        evaluator = PersonaEvaluationFramework()
        persona = PersonaProfile(
            name="Test",
            category=PersonaCategory.SPECIALIST,
            description="Test persona.",
            status=PersonaStatus.ACTIVE,
        )
        for score, expected_grade in [(92, "A"), (82, "B"), (72, "C"), (62, "D"), (50, "F")]:
            sc = await evaluator.evaluate(persona, _make_metrics(persona.persona_id, float(score)))
            assert sc.grade == expected_grade, f"score={score} expected {expected_grade} got {sc.grade}"

    async def test_batch_evaluate(self):
        registry = PersonaRegistry()
        evaluator = PersonaEvaluationFramework()
        report = await evaluator.batch_evaluate(registry.list_all())
        assert len(report.scorecards) == 6
        assert report.top_performer_id is not None

    async def test_retirement_candidates(self):
        evaluator = PersonaEvaluationFramework()
        low_scorer = PersonaProfile(
            name="Low Performer",
            category=PersonaCategory.SPECIALIST,
            description="Consistently underperforms.",
            status=PersonaStatus.ACTIVE,
            performance_score=20.0,
        )
        report = await evaluator.batch_evaluate([low_scorer])
        assert low_scorer.persona_id in report.retirement_candidates

    async def test_improvement_recommendations(self):
        registry = PersonaRegistry()
        evaluator = PersonaEvaluationFramework()
        persona = registry.get("PERSONA-REVENUE-01")
        # Give it low sub-metric scores to trigger improvement areas
        metrics = _make_metrics("PERSONA-REVENUE-01", 40.0)
        scorecard = await evaluator.evaluate(persona, metrics)
        recs = await evaluator.get_improvement_recommendations(scorecard)
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_health_check(self):
        evaluator = PersonaEvaluationFramework()
        health = evaluator.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaEvaluationFramework"
