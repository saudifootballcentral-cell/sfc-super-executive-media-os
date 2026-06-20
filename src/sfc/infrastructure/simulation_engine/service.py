"""Simulation Engine — predict outcomes before execution using historical benchmarks."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus
from sfc.infrastructure.simulation_engine.models import (
    SimulationComparison,
    SimulationResult,
    SimulationScenario,
)

logger = logging.getLogger("sfc.infrastructure.simulation_engine")

# ---------------------------------------------------------------------------
# Platform benchmarks
# ---------------------------------------------------------------------------
_BASE_REACH: dict[str, int] = {
    "tiktok": 500_000,
    "instagram_reels": 300_000,
    "instagram_stories": 200_000,
    "instagram_feed": 150_000,
    "youtube_shorts": 400_000,
    "youtube": 250_000,
    "x": 180_000,
    "telegram": 80_000,
    "whatsapp": 60_000,
    "website": 50_000,
    "newsletter": 30_000,
}
_DEFAULT_PLATFORM_REACH = 100_000

_PLATFORM_ENGAGEMENT: dict[str, float] = {
    "tiktok": 0.12,
    "instagram_reels": 0.09,
    "instagram_stories": 0.06,
    "instagram_feed": 0.05,
    "youtube_shorts": 0.08,
    "youtube": 0.07,
    "x": 0.04,
    "telegram": 0.15,
    "whatsapp": 0.20,
    "website": 0.03,
    "newsletter": 0.25,
}

_PLATFORM_CPM: dict[str, float] = {
    "youtube": 4.5,
    "youtube_shorts": 2.0,
    "instagram_reels": 3.5,
    "instagram_stories": 2.5,
    "instagram_feed": 3.0,
    "tiktok": 2.0,
    "x": 1.5,
    "website": 2.5,
    "telegram": 0.5,
    "whatsapp": 0.0,
    "newsletter": 5.0,
}

# Task type multipliers
_TASK_REACH_MULTIPLIER: dict[str, float] = {
    "transfer": 1.8,
    "crisis": 1.6,
    "match": 1.5,
    "trend": 1.4,
    "campaign": 1.3,
    "news": 1.2,
    "analysis": 1.0,
}

_TASK_VIRALITY: dict[str, float] = {
    "transfer": 90.0,
    "crisis": 85.0,
    "match": 75.0,
    "trend": 70.0,
    "campaign": 65.0,
    "news": 60.0,
    "analysis": 45.0,
}

_TASK_STRATEGIC_VALUE: dict[str, float] = {
    "campaign": 90.0,
    "transfer": 85.0,
    "crisis": 80.0,
    "match": 75.0,
    "analysis": 70.0,
    "trend": 65.0,
    "news": 60.0,
}

_TIMING_MULTIPLIER: dict[str, float] = {
    "breaking": 2.0,
    "live": 1.8,
    "urgent": 1.5,
    "standard": 1.0,
    "scheduled": 0.8,
    "evergreen": 0.7,
}

_WATCH_TIME_BASE: dict[str, int] = {
    "video": 4,
    "short_video": 2,
    "article": 3,
    "analysis": 6,
    "podcast": 15,
    "newsletter": 5,
    "social_post": 1,
}


class SimulationEngineService:
    """Deterministic simulation engine using historical benchmarks + probability models.

    No external API calls — all predictions are derived from configured benchmarks.
    """

    def _compute_result(self, scenario: SimulationScenario) -> SimulationResult:
        """Core simulation logic."""
        task_type = scenario.task_type.lower()
        timing = scenario.timing.lower()
        confidence = scenario.confidence_score
        source_count = scenario.source_count

        # --- Reach ---
        total_platform_reach = sum(
            _BASE_REACH.get(p.lower(), _DEFAULT_PLATFORM_REACH)
            for p in scenario.platforms
        )
        confidence_multiplier = 0.5 + (confidence / 200.0)  # 0.5-1.0
        task_multiplier = _TASK_REACH_MULTIPLIER.get(task_type, 1.0)
        timing_multiplier = _TIMING_MULTIPLIER.get(timing, 1.0)
        source_multiplier = min(1.0 + (source_count - 2) * 0.05, 1.3)

        expected_reach = int(
            total_platform_reach
            * confidence_multiplier
            * task_multiplier
            * timing_multiplier
            * source_multiplier
        )

        # --- Engagement Rate ---
        avg_engagement = (
            sum(_PLATFORM_ENGAGEMENT.get(p.lower(), 0.05) for p in scenario.platforms)
            / max(len(scenario.platforms), 1)
        )
        quality_score = confidence / 100.0
        hook_strength = _TASK_REACH_MULTIPLIER.get(task_type, 1.0) / 2.0  # 0.5-0.9
        engagement_rate = avg_engagement * quality_score * (1 + hook_strength * 0.2)
        engagement_rate = min(engagement_rate, 0.50)

        # --- Watch Time ---
        content_type = scenario.content_type.lower()
        watch_time_base = _WATCH_TIME_BASE.get(content_type, 3)
        watch_time = int(watch_time_base * (0.7 + confidence / 333.0))

        # --- Revenue ---
        avg_cpm = (
            sum(_PLATFORM_CPM.get(p.lower(), 2.0) for p in scenario.platforms)
            / max(len(scenario.platforms), 1)
        )
        impressions = expected_reach * engagement_rate
        revenue = (impressions / 1000.0) * avg_cpm * quality_score

        # --- Virality ---
        virality = _TASK_VIRALITY.get(task_type, 60.0)
        # Adjust for timing and confidence
        virality = virality * timing_multiplier * (0.7 + confidence / 333.0)
        virality = min(virality, 100.0)

        # --- Risk ---
        # High confidence + multiple sources = lower risk
        base_risk = 100.0 - confidence
        source_discount = min((source_count - 1) * 5.0, 25.0)
        risk_score = max(base_risk - source_discount, 5.0)
        risk_score = min(risk_score, 95.0)

        # --- Strategic Value ---
        strategic_value = _TASK_STRATEGIC_VALUE.get(task_type, 60.0)
        platform_coverage = min(len(scenario.platforms) / 4.0, 1.0)
        strategic_value = strategic_value * (0.8 + platform_coverage * 0.2)
        strategic_value = min(strategic_value, 100.0)

        # --- Overall Score --- (composite, weighted)
        overall_score = (
            virality * 0.25
            + (100.0 - risk_score) * 0.20
            + strategic_value * 0.25
            + min(engagement_rate * 1000, 100.0) * 0.15
            + confidence * 0.15
        )
        overall_score = min(overall_score, 100.0)

        return SimulationResult(
            scenario_id=scenario.scenario_id,
            expected_reach=expected_reach,
            expected_engagement_rate=round(engagement_rate, 4),
            expected_watch_time_minutes=watch_time,
            expected_revenue_usd=round(revenue, 2),
            virality_score=round(virality, 1),
            risk_score=round(risk_score, 1),
            strategic_value=round(strategic_value, 1),
            overall_score=round(overall_score, 1),
            confidence=round(confidence, 1),
            simulated_at=datetime.utcnow(),
        )

    async def simulate(self, scenario: SimulationScenario) -> SimulationResult:
        """Run a single scenario simulation."""
        result = self._compute_result(scenario)
        logger.info(
            "[SimEngine] Simulated %s: reach=%d overall=%.1f risk=%.1f",
            scenario.name,
            result.expected_reach,
            result.overall_score,
            result.risk_score,
        )
        return result

    async def compare(
        self,
        scenarios: list[SimulationScenario],
    ) -> SimulationComparison:
        """Run all scenarios and return comparison with recommendation."""
        results: list[SimulationResult] = []
        for scenario in scenarios:
            result = self._compute_result(scenario)
            results.append(result)

        # Recommend the scenario with highest overall_score and risk < 60
        eligible = [r for r in results if r.risk_score < 60]
        if not eligible:
            eligible = results  # relax risk constraint

        best = max(eligible, key=lambda r: r.overall_score)

        # Build rationale
        scenario_name_map = {s.scenario_id: s.name for s in scenarios}
        best_name = scenario_name_map.get(best.scenario_id, best.scenario_id)
        rationale = (
            f"'{best_name}' recommended: overall score {best.overall_score:.1f}/100, "
            f"virality {best.virality_score:.1f}, risk {best.risk_score:.1f}, "
            f"strategic value {best.strategic_value:.1f}. "
            f"Expected reach: {best.expected_reach:,}."
        )

        return SimulationComparison(
            scenarios=results,
            recommended_scenario_id=best.scenario_id,
            recommendation_rationale=rationale,
            compared_at=datetime.utcnow(),
        )

    async def simulate_content_performance(
        self,
        content_type: str,
        platforms: list[str],
        task_type: str,
        confidence_score: float,
        source_count: int,
    ) -> SimulationResult:
        """Predict performance for a specific content piece."""
        scenario = SimulationScenario(
            name=f"Content:{content_type}:{task_type}",
            content_type=content_type,
            platforms=platforms,
            task_type=task_type,
            confidence_score=confidence_score,
            source_count=source_count,
        )
        return await self.simulate(scenario)

    async def simulate_revenue(
        self,
        content_type: str,
        platforms: list[str],
        sponsor_signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Predict revenue outcomes."""
        scenario = SimulationScenario(
            name=f"Revenue:{content_type}",
            content_type=content_type,
            platforms=platforms,
            task_type="campaign",
            confidence_score=85.0,
        )
        result = self._compute_result(scenario)

        # Sponsor bonus
        sponsor_bonus = sum(
            signal.get("value_usd", 0) * 0.1 for signal in sponsor_signals
        )

        return {
            "base_revenue_usd": result.expected_revenue_usd,
            "sponsor_bonus_usd": round(sponsor_bonus, 2),
            "total_revenue_usd": round(result.expected_revenue_usd + sponsor_bonus, 2),
            "reach": result.expected_reach,
            "engagement_rate": result.expected_engagement_rate,
            "sponsor_count": len(sponsor_signals),
            "revenue_per_1k_reach": round(
                result.expected_revenue_usd / max(result.expected_reach / 1000, 1), 2
            ),
        }

    def health_check(self) -> ComponentHealth:
        """Return health status of the simulation engine."""
        try:
            # Run a quick self-test
            test_scenario = SimulationScenario(
                name="health_check",
                content_type="video",
                platforms=["youtube"],
                task_type="news",
                confidence_score=85.0,
            )
            result = self._compute_result(test_scenario)
            assert result.expected_reach > 0
            assert 0 <= result.overall_score <= 100

            return ComponentHealth(
                component="simulation_engine",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow(),
                metrics={
                    "self_test_reach": result.expected_reach,
                    "self_test_score": result.overall_score,
                },
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="simulation_engine",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
