"""Tests for StrategicPlanningService — ICE scoring, plan creation, weekly missions."""

from __future__ import annotations

import pytest

from sfc.divisions.base import DivisionInput
from sfc.divisions.strategic_planning.service import StrategicPlanningService


def _make_input(task_type: str = "news", payload: dict | None = None) -> DivisionInput:
    return DivisionInput(
        run_id="test-run-001",
        task_type=task_type,
        payload=payload or {},
        state_snapshot={
            "run_id": "test-run-001",
            "task_type": task_type,
            "task_payload": payload or {},
            "executive_decision": {
                "priority": "high",
                "recommended_divisions": ["intelligence", "editorial", "governance", "publishing"],
            },
        },
    )


class TestStrategicPlanningServiceLifecycle:
    async def test_initialize_and_shutdown(self) -> None:
        service = StrategicPlanningService()
        await service.initialize()
        await service.shutdown()

    def test_health_check_returns_healthy(self) -> None:
        service = StrategicPlanningService()
        health = service.health_check()
        assert health.status == "healthy"
        assert health.division == "strategic_planning"

    def test_describe_returns_string(self) -> None:
        service = StrategicPlanningService()
        assert len(service.describe()) > 5


class TestICEScoring:
    async def test_prioritize_returns_ice_scores(self) -> None:
        service = StrategicPlanningService()
        items = [
            {"name": "TikTok campaign", "impact": 9, "confidence": 8, "ease": 7},
            {"name": "Newsletter", "impact": 5, "confidence": 6, "ease": 8},
            {"name": "YouTube long", "impact": 7, "confidence": 5, "ease": 4},
        ]
        result = await service.prioritize(items)
        assert len(result) == 3
        for item in result:
            assert "ice_score" in item

    async def test_prioritize_sorts_descending(self) -> None:
        service = StrategicPlanningService()
        items = [
            {"name": "Low", "impact": 1, "confidence": 1, "ease": 1},
            {"name": "High", "impact": 10, "confidence": 10, "ease": 10},
            {"name": "Mid", "impact": 5, "confidence": 5, "ease": 5},
        ]
        result = await service.prioritize(items)
        scores = [r["ice_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    async def test_ice_formula_is_product(self) -> None:
        service = StrategicPlanningService()
        item = {"name": "test", "impact": 4.0, "confidence": 5.0, "ease": 3.0}
        result = await service.prioritize([item])
        expected_ice = 4.0 * 5.0 * 3.0
        assert result[0]["ice_score"] == expected_ice

    async def test_prioritize_empty_list(self) -> None:
        service = StrategicPlanningService()
        result = await service.prioritize([])
        assert result == []

    async def test_prioritize_missing_scores_use_defaults(self) -> None:
        service = StrategicPlanningService()
        items = [{"name": "no scores"}]
        result = await service.prioritize(items)
        assert len(result) == 1
        # Should default to 5×5×5 = 125
        assert result[0]["ice_score"] == 125.0


class TestAnnualPlanCreation:
    async def test_create_annual_plan_returns_structure(self) -> None:
        service = StrategicPlanningService()
        plan = await service.create_annual_plan(
            "Become the #1 Saudi football media brand", 500000.0
        )
        assert "plan_id" in plan
        assert "quarterly_milestones" in plan
        assert "Q1" in plan["quarterly_milestones"]
        assert "Q4" in plan["quarterly_milestones"]

    async def test_annual_plan_includes_budget(self) -> None:
        service = StrategicPlanningService()
        plan = await service.create_annual_plan("vision", 250000.0)
        assert plan["budget_usd"] == 250000.0

    async def test_annual_plan_includes_vision(self) -> None:
        service = StrategicPlanningService()
        vision = "Dominate Saudi football digital media"
        plan = await service.create_annual_plan(vision, 100000.0)
        assert plan["vision"] == vision


class TestWeeklyMissionCreation:
    async def test_create_weekly_mission_returns_5_days(self) -> None:
        service = StrategicPlanningService()
        missions = await service.create_weekly_mission({"task_type": "news"})
        assert len(missions) == 5

    async def test_each_mission_has_required_fields(self) -> None:
        service = StrategicPlanningService()
        missions = await service.create_weekly_mission({"task_type": "transfer"})
        for mission in missions:
            assert "day" in mission
            assert "mission" in mission
            assert "objective" in mission

    async def test_missions_span_weekdays(self) -> None:
        service = StrategicPlanningService()
        missions = await service.create_weekly_mission({"task_type": "match"})
        days = [m["day"] for m in missions]
        assert "Monday" in days
        assert "Friday" in days


class TestStrategicPlanningExecute:
    async def test_execute_returns_execution_plan(self) -> None:
        service = StrategicPlanningService()
        await service.initialize()
        result = await service.execute(_make_input("news"))
        assert result.success is True
        assert "execution_plan" in result.data

    async def test_execute_transfer_type_targets_relevant_platforms(self) -> None:
        service = StrategicPlanningService()
        await service.initialize()
        result = await service.execute(_make_input("transfer"))
        plan = result.data.get("execution_plan", {})
        platforms = plan.get("platforms_targeted", [])
        # Transfer should target TikTok and Instagram
        platform_values = [p if isinstance(p, str) else p.value for p in platforms]
        assert any("tiktok" in str(p) for p in platform_values)

    async def test_execute_crisis_type_uses_fast_platforms(self) -> None:
        service = StrategicPlanningService()
        await service.initialize()
        result = await service.execute(_make_input("crisis"))
        plan = result.data.get("execution_plan", {})
        platforms = plan.get("platforms_targeted", [])
        platform_values = [p if isinstance(p, str) else str(p) for p in platforms]
        # Crisis should target X and Telegram
        assert any("x" in str(p).lower() or "telegram" in str(p).lower() for p in platform_values)

    async def test_execute_includes_weekly_missions(self) -> None:
        service = StrategicPlanningService()
        await service.initialize()
        result = await service.execute(_make_input("news"))
        assert "weekly_missions" in result.data
        assert len(result.data["weekly_missions"]) == 5

    async def test_execute_includes_prioritized_items(self) -> None:
        service = StrategicPlanningService()
        await service.initialize()
        result = await service.execute(_make_input("news"))
        assert "prioritized_items" in result.data

    async def test_validate_task_type_required(self) -> None:
        service = StrategicPlanningService()
        result = await service.validate({"task_type": "news"})
        assert result.valid is True

    async def test_validate_missing_task_type(self) -> None:
        service = StrategicPlanningService()
        result = await service.validate({})
        assert result.valid is False
