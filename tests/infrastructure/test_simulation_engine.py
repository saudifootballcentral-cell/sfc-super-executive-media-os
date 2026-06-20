"""Tests for SimulationEngineService."""

from __future__ import annotations

import pytest

from sfc.infrastructure.simulation_engine.service import SimulationEngineService
from sfc.infrastructure.simulation_engine.models import (
    SimulationComparison,
    SimulationResult,
    SimulationScenario,
)
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus


@pytest.fixture
def engine() -> SimulationEngineService:
    return SimulationEngineService()


def make_scenario(
    name: str = "test",
    content_type: str = "video",
    platforms: list[str] | None = None,
    task_type: str = "news",
    confidence_score: float = 85.0,
    source_count: int = 3,
    timing: str = "standard",
) -> SimulationScenario:
    return SimulationScenario(
        name=name,
        content_type=content_type,
        platforms=platforms or ["youtube", "tiktok"],
        task_type=task_type,
        confidence_score=confidence_score,
        source_count=source_count,
        timing=timing,
    )


@pytest.mark.asyncio
async def test_simulate_returns_result(engine: SimulationEngineService) -> None:
    """simulate() returns a SimulationResult with all required fields."""
    scenario = make_scenario()
    result = await engine.simulate(scenario)

    assert isinstance(result, SimulationResult)
    assert result.scenario_id == scenario.scenario_id
    assert result.expected_reach > 0
    assert 0.0 <= result.expected_engagement_rate <= 1.0
    assert result.expected_watch_time_minutes >= 0
    assert result.expected_revenue_usd >= 0.0
    assert 0.0 <= result.virality_score <= 100.0
    assert 0.0 <= result.risk_score <= 100.0
    assert 0.0 <= result.strategic_value <= 100.0
    assert 0.0 <= result.overall_score <= 100.0
    assert 0.0 <= result.confidence <= 100.0
    assert result.simulated_at is not None


@pytest.mark.asyncio
async def test_simulate_higher_confidence_higher_score(engine: SimulationEngineService) -> None:
    """Higher confidence_score leads to higher overall_score."""
    low_conf = make_scenario(name="low", confidence_score=50.0)
    high_conf = make_scenario(name="high", confidence_score=95.0)

    low_result = await engine.simulate(low_conf)
    high_result = await engine.simulate(high_conf)

    assert high_result.overall_score > low_result.overall_score


@pytest.mark.asyncio
async def test_simulate_higher_confidence_lower_risk(engine: SimulationEngineService) -> None:
    """Higher confidence_score leads to lower risk_score."""
    low_conf = make_scenario(name="low", confidence_score=40.0, source_count=1)
    high_conf = make_scenario(name="high", confidence_score=95.0, source_count=5)

    low_result = await engine.simulate(low_conf)
    high_result = await engine.simulate(high_conf)

    assert high_result.risk_score < low_result.risk_score


@pytest.mark.asyncio
async def test_simulate_crisis_task_high_virality(engine: SimulationEngineService) -> None:
    """Crisis task type produces high virality score."""
    crisis = make_scenario(task_type="crisis")
    news = make_scenario(task_type="news")

    crisis_result = await engine.simulate(crisis)
    news_result = await engine.simulate(news)

    assert crisis_result.virality_score > news_result.virality_score
    assert crisis_result.virality_score >= 70.0  # Crisis should be high virality


@pytest.mark.asyncio
async def test_simulate_transfer_task_high_virality(engine: SimulationEngineService) -> None:
    """Transfer task type produces highest virality score."""
    transfer = make_scenario(task_type="transfer")
    result = await engine.simulate(transfer)
    assert result.virality_score >= 80.0


@pytest.mark.asyncio
async def test_simulate_breaking_timing_boosts_reach(engine: SimulationEngineService) -> None:
    """Breaking timing multiplier increases expected reach."""
    standard = make_scenario(name="standard", timing="standard")
    breaking = make_scenario(name="breaking", timing="breaking")

    standard_result = await engine.simulate(standard)
    breaking_result = await engine.simulate(breaking)

    assert breaking_result.expected_reach > standard_result.expected_reach


@pytest.mark.asyncio
async def test_simulate_more_platforms_higher_reach(engine: SimulationEngineService) -> None:
    """More platforms leads to higher expected reach."""
    one_platform = make_scenario(name="one", platforms=["youtube"])
    many_platforms = make_scenario(
        name="many",
        platforms=["youtube", "tiktok", "instagram_reels", "x"],
    )

    one_result = await engine.simulate(one_platform)
    many_result = await engine.simulate(many_platforms)

    assert many_result.expected_reach > one_result.expected_reach


@pytest.mark.asyncio
async def test_compare_returns_comparison(engine: SimulationEngineService) -> None:
    """compare() returns SimulationComparison with a recommendation."""
    scenarios = [
        make_scenario(name="Option A", task_type="transfer", timing="breaking"),
        make_scenario(name="Option B", task_type="news", timing="standard"),
        make_scenario(name="Option C", task_type="match", timing="live"),
    ]

    comparison = await engine.compare(scenarios)

    assert isinstance(comparison, SimulationComparison)
    assert len(comparison.scenarios) == 3
    assert comparison.recommended_scenario_id in [s.scenario_id for s in scenarios]
    assert isinstance(comparison.recommendation_rationale, str)
    assert len(comparison.recommendation_rationale) > 0
    assert comparison.compared_at is not None


@pytest.mark.asyncio
async def test_compare_recommends_best_scenario(engine: SimulationEngineService) -> None:
    """compare() recommends the scenario with the best overall score."""
    # Low confidence + low quality scenario
    bad = SimulationScenario(
        name="Bad Option",
        content_type="social_post",
        platforms=["website"],
        task_type="analysis",
        timing="evergreen",
        confidence_score=40.0,
        source_count=1,
    )
    # High confidence + high quality scenario
    good = SimulationScenario(
        name="Good Option",
        content_type="video",
        platforms=["youtube", "tiktok", "instagram_reels"],
        task_type="transfer",
        timing="breaking",
        confidence_score=95.0,
        source_count=5,
    )

    comparison = await engine.compare([bad, good])
    assert comparison.recommended_scenario_id == good.scenario_id


@pytest.mark.asyncio
async def test_simulate_content_performance(engine: SimulationEngineService) -> None:
    """simulate_content_performance() returns a valid result."""
    result = await engine.simulate_content_performance(
        content_type="video",
        platforms=["youtube", "instagram_reels"],
        task_type="match",
        confidence_score=88.0,
        source_count=3,
    )

    assert isinstance(result, SimulationResult)
    assert result.expected_reach > 0
    assert result.overall_score > 0


@pytest.mark.asyncio
async def test_simulate_revenue(engine: SimulationEngineService) -> None:
    """simulate_revenue() returns revenue prediction dict."""
    revenue = await engine.simulate_revenue(
        content_type="video",
        platforms=["youtube", "tiktok"],
        sponsor_signals=[{"value_usd": 10000}, {"value_usd": 5000}],
    )

    assert "base_revenue_usd" in revenue
    assert "sponsor_bonus_usd" in revenue
    assert "total_revenue_usd" in revenue
    assert revenue["total_revenue_usd"] >= revenue["base_revenue_usd"]
    assert revenue["sponsor_bonus_usd"] > 0  # Has sponsors


@pytest.mark.asyncio
async def test_simulate_revenue_no_sponsors(engine: SimulationEngineService) -> None:
    """simulate_revenue() works with empty sponsor list."""
    revenue = await engine.simulate_revenue(
        content_type="article",
        platforms=["website", "newsletter"],
        sponsor_signals=[],
    )

    assert revenue["sponsor_bonus_usd"] == 0.0
    assert revenue["total_revenue_usd"] == revenue["base_revenue_usd"]


def test_health_check_returns_component_health(engine: SimulationEngineService) -> None:
    """health_check() returns ComponentHealth without raising."""
    health = engine.health_check()
    assert isinstance(health, ComponentHealth)
    assert health.component == "simulation_engine"
    assert health.status == HealthStatus.HEALTHY


def test_health_check_never_raises(engine: SimulationEngineService) -> None:
    """health_check() must never raise."""
    health = engine.health_check()
    assert health is not None


@pytest.mark.asyncio
async def test_risk_score_bounded(engine: SimulationEngineService) -> None:
    """Risk score stays in 0-100 range."""
    # Edge case: extremely low confidence
    scenario = make_scenario(confidence_score=5.0, source_count=1)
    result = await engine.simulate(scenario)
    assert 0.0 <= result.risk_score <= 100.0


@pytest.mark.asyncio
async def test_overall_score_bounded(engine: SimulationEngineService) -> None:
    """Overall score stays in 0-100 range."""
    for task_type in ["news", "match", "transfer", "crisis", "trend", "analysis", "campaign"]:
        scenario = make_scenario(task_type=task_type)
        result = await engine.simulate(scenario)
        assert 0.0 <= result.overall_score <= 100.0, f"Out of bounds for task_type={task_type}"
