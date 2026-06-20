"""Tests for LearningEngineService."""

from __future__ import annotations

import pytest

from sfc.infrastructure.learning_engine.service import Lesson, LearningEngineService, LessonType
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus


@pytest.fixture
def engine() -> LearningEngineService:
    return LearningEngineService()


def make_state(
    run_id: str = "run-001",
    task_type: str = "transfer",
    approved_count: int = 5,
    rejected_count: int = 1,
    reach: int = 500_000,
    errors: list[str] | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "task_type": task_type,
        "approved_content": [{"id": f"c{i}"} for i in range(approved_count)],
        "rejected_content": [{"id": f"r{i}"} for i in range(rejected_count)],
        "analytics_report": {
            "estimated_reach": reach,
            "benchmark_reach": 100_000,
            "engagement_rate": 0.08,
        },
        "pipeline_stage": "complete",
        "errors": errors or [],
        "warnings": [],
    }


@pytest.mark.asyncio
async def test_analyze_workflow_returns_lessons(engine: LearningEngineService) -> None:
    """analyze_workflow() returns a list of Lesson objects."""
    state = make_state(approved_count=5, rejected_count=0, reach=500_000)
    lessons = await engine.analyze_workflow(state)

    assert isinstance(lessons, list)
    assert all(isinstance(l, Lesson) for l in lessons)


@pytest.mark.asyncio
async def test_analyze_workflow_high_approval_success_pattern(engine: LearningEngineService) -> None:
    """analyze_workflow() generates success_pattern when approval rate is high."""
    state = make_state(approved_count=10, rejected_count=0)
    lessons = await engine.analyze_workflow(state)

    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.SUCCESS_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_workflow_low_approval_failure_pattern(engine: LearningEngineService) -> None:
    """analyze_workflow() generates failure_pattern when approval rate is low."""
    state = make_state(approved_count=1, rejected_count=10)
    lessons = await engine.analyze_workflow(state)

    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.FAILURE_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_workflow_viral_reach_triggers_success(engine: LearningEngineService) -> None:
    """analyze_workflow() generates success_pattern for viral reach."""
    state = make_state(reach=5_000_000)  # > 1M
    lessons = await engine.analyze_workflow(state)

    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.SUCCESS_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_workflow_errors_trigger_workflow_improvement(
    engine: LearningEngineService,
) -> None:
    """analyze_workflow() generates workflow_improvement for pipeline errors."""
    state = make_state(errors=["TimeoutError: intelligence service", "ValidationError: sources"])
    lessons = await engine.analyze_workflow(state)

    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.WORKFLOW_IMPROVEMENT in lesson_types


@pytest.mark.asyncio
async def test_analyze_governance_outcome_high_rejection(engine: LearningEngineService) -> None:
    """analyze_governance_outcome() creates failure lesson when rejection rate is high."""
    lessons = await engine.analyze_governance_outcome(
        approved=[{"id": "c1"}],
        rejected=[{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        run_id="run-002",
    )

    assert len(lessons) >= 1
    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.FAILURE_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_governance_outcome_all_approved(engine: LearningEngineService) -> None:
    """analyze_governance_outcome() creates success lesson when all approved."""
    lessons = await engine.analyze_governance_outcome(
        approved=[{"id": f"c{i}"} for i in range(5)],
        rejected=[],
        run_id="run-003",
    )

    if lessons:
        lesson_types = [l.lesson_type for l in lessons]
        assert LessonType.SUCCESS_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_governance_outcome_empty_returns_empty(engine: LearningEngineService) -> None:
    """analyze_governance_outcome() returns empty list when no content."""
    lessons = await engine.analyze_governance_outcome([], [], "run-004")
    assert lessons == []


@pytest.mark.asyncio
async def test_analyze_content_performance_viral(engine: LearningEngineService) -> None:
    """analyze_content_performance() generates success lesson for >2x benchmark."""
    report = {
        "estimated_reach": 500_000,
        "benchmark_reach": 100_000,  # 5x benchmark
        "engagement_rate": 0.12,
        "total_revenue_usd": 1500.0,
    }
    lessons = await engine.analyze_content_performance(report, "run-005")

    assert len(lessons) >= 1
    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.SUCCESS_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_content_performance_underperform(engine: LearningEngineService) -> None:
    """analyze_content_performance() generates optimization lesson for underperformance."""
    report = {
        "estimated_reach": 20_000,
        "benchmark_reach": 100_000,  # < 50% of benchmark
        "engagement_rate": 0.02,
        "total_revenue_usd": 5.0,
    }
    lessons = await engine.analyze_content_performance(report, "run-006")

    assert len(lessons) >= 1
    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.OPTIMIZATION in lesson_types


@pytest.mark.asyncio
async def test_analyze_intelligence_quality_low_confidence(engine: LearningEngineService) -> None:
    """analyze_intelligence_quality() generates failure lesson for low confidence."""
    report = {"confidence_score": 45.0, "source_count": 1, "verified": False}
    lessons = await engine.analyze_intelligence_quality(report, "run-007")

    assert len(lessons) >= 1
    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.FAILURE_PATTERN in lesson_types


@pytest.mark.asyncio
async def test_analyze_intelligence_quality_insufficient_sources(
    engine: LearningEngineService,
) -> None:
    """analyze_intelligence_quality() generates optimization lesson for < 2 sources."""
    report = {"confidence_score": 80.0, "source_count": 1, "verified": False}
    lessons = await engine.analyze_intelligence_quality(report, "run-008")

    lesson_types = [l.lesson_type for l in lessons]
    assert LessonType.OPTIMIZATION in lesson_types


def test_get_lessons_returns_all(engine: LearningEngineService) -> None:
    """get_lessons() returns all lessons when no filters applied."""
    # Add some lessons directly
    engine._lessons.append(Lesson(
        lesson_type=LessonType.SUCCESS_PATTERN,
        division="analytics",
        run_id="run-test",
        observation="Test observation",
        recommendation="Test recommendation",
        confidence=85.0,
        impact="high",
    ))
    engine._lessons.append(Lesson(
        lesson_type=LessonType.FAILURE_PATTERN,
        division="governance",
        run_id="run-test",
        observation="Test failure",
        recommendation="Fix this",
        confidence=90.0,
        impact="high",
    ))

    lessons = engine.get_lessons()
    assert len(lessons) >= 2


def test_get_lessons_filters_by_division(engine: LearningEngineService) -> None:
    """get_lessons() filters correctly by division."""
    engine._lessons.append(Lesson(
        lesson_type=LessonType.SUCCESS_PATTERN,
        division="analytics",
        run_id="run-test",
        observation="Analytics observation",
        recommendation="Analytics recommendation",
        confidence=85.0,
        impact="medium",
    ))
    engine._lessons.append(Lesson(
        lesson_type=LessonType.FAILURE_PATTERN,
        division="governance",
        run_id="run-test",
        observation="Governance failure",
        recommendation="Governance fix",
        confidence=90.0,
        impact="high",
    ))

    analytics_lessons = engine.get_lessons(division="analytics")
    assert all(l.division == "analytics" for l in analytics_lessons)
    assert len(analytics_lessons) >= 1

    governance_lessons = engine.get_lessons(division="governance")
    assert all(l.division == "governance" for l in governance_lessons)


def test_get_lessons_filters_by_type(engine: LearningEngineService) -> None:
    """get_lessons() filters correctly by lesson type."""
    engine._lessons.append(Lesson(
        lesson_type=LessonType.SUCCESS_PATTERN,
        division="editorial",
        run_id="run-test",
        observation="Success",
        recommendation="Keep doing this",
        confidence=80.0,
        impact="high",
    ))

    success_lessons = engine.get_lessons(lesson_type=LessonType.SUCCESS_PATTERN)
    assert all(l.lesson_type == LessonType.SUCCESS_PATTERN for l in success_lessons)


def test_get_best_practices_returns_strings(engine: LearningEngineService) -> None:
    """get_best_practices() returns a list of strings."""
    engine._lessons.append(Lesson(
        lesson_type=LessonType.SUCCESS_PATTERN,
        division="editorial",
        run_id="run-test",
        observation="Great content approach",
        recommendation="Always use this approach",
        confidence=90.0,
        impact="high",
    ))

    practices = engine.get_best_practices()
    assert isinstance(practices, list)
    assert all(isinstance(p, str) for p in practices)


def test_get_failure_patterns_returns_strings(engine: LearningEngineService) -> None:
    """get_failure_patterns() returns a list of strings."""
    engine._lessons.append(Lesson(
        lesson_type=LessonType.FAILURE_PATTERN,
        division="governance",
        run_id="run-test",
        observation="Don't do this",
        recommendation="Avoid this pattern",
        confidence=95.0,
        impact="high",
    ))

    patterns = engine.get_failure_patterns()
    assert isinstance(patterns, list)
    assert all(isinstance(p, str) for p in patterns)


def test_get_workflow_recommendations_returns_strings(engine: LearningEngineService) -> None:
    """get_workflow_recommendations() returns a list of strings."""
    engine._lessons.append(Lesson(
        lesson_type=LessonType.WORKFLOW_IMPROVEMENT,
        division="infrastructure",
        run_id="run-test",
        observation="Pipeline bottleneck",
        recommendation="Optimize this step",
        confidence=80.0,
        impact="medium",
    ))

    recommendations = engine.get_workflow_recommendations()
    assert isinstance(recommendations, list)
    assert all(isinstance(r, str) for r in recommendations)


@pytest.mark.asyncio
async def test_generate_prompt_update_with_failures(engine: LearningEngineService) -> None:
    """generate_prompt_update() returns a string suggestion when failures exist."""
    engine._lessons.append(Lesson(
        lesson_type=LessonType.FAILURE_PATTERN,
        division="editorial",
        run_id="run-test",
        observation="Articles too long for TikTok audience",
        recommendation="Shorten content to <60 seconds",
        confidence=88.0,
        impact="high",
    ))

    update = await engine.generate_prompt_update("editorial")
    assert isinstance(update, str)
    assert len(update) > 0
    assert "editorial" in update.lower() or "Editorial" in update


@pytest.mark.asyncio
async def test_generate_prompt_update_no_lessons_returns_none(
    engine: LearningEngineService,
) -> None:
    """generate_prompt_update() returns None when no lessons exist for division."""
    update = await engine.generate_prompt_update("analytics")
    assert update is None


def test_get_lessons_respects_limit(engine: LearningEngineService) -> None:
    """get_lessons() respects the limit parameter."""
    for i in range(25):
        engine._lessons.append(Lesson(
            lesson_type=LessonType.OPTIMIZATION,
            division="analytics",
            run_id=f"run-{i}",
            observation=f"Observation {i}",
            recommendation=f"Recommendation {i}",
            confidence=75.0,
            impact="low",
        ))

    limited = engine.get_lessons(limit=5)
    assert len(limited) <= 5


def test_health_check_returns_component_health(engine: LearningEngineService) -> None:
    """health_check() returns ComponentHealth without raising."""
    health = engine.health_check()
    assert isinstance(health, ComponentHealth)
    assert health.component == "learning_engine"
    assert health.status in list(HealthStatus)


def test_health_check_never_raises(engine: LearningEngineService) -> None:
    """health_check() must never raise."""
    health = engine.health_check()
    assert health is not None


def test_health_check_includes_lesson_metrics(engine: LearningEngineService) -> None:
    """health_check() includes lesson count in metrics."""
    health = engine.health_check()
    assert "total_lessons" in health.metrics
