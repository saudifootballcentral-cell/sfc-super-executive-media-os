"""Tests for scheduler trigger types and conditions."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sfc.scheduler.triggers import (
    TriggerCondition,
    TriggerConfig,
    TriggerType,
    make_cost_exceeded_trigger,
    make_crisis_trigger,
)


class TestTriggerCondition:
    def test_always_true(self):
        cond = TriggerCondition(condition_type="always")
        assert cond.evaluate({}) is True
        assert cond.evaluate({"anything": "here"}) is True

    def test_threshold_gt(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="cost",
            threshold=50.0,
            comparison="gt",
        )
        assert cond.evaluate({"cost": 51.0}) is True
        assert cond.evaluate({"cost": 50.0}) is False
        assert cond.evaluate({"cost": 49.0}) is False

    def test_threshold_gte(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="cost",
            threshold=50.0,
            comparison="gte",
        )
        assert cond.evaluate({"cost": 50.0}) is True
        assert cond.evaluate({"cost": 50.01}) is True
        assert cond.evaluate({"cost": 49.99}) is False

    def test_threshold_lt(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="reach",
            threshold=10000,
            comparison="lt",
        )
        assert cond.evaluate({"reach": 9999}) is True
        assert cond.evaluate({"reach": 10000}) is False

    def test_threshold_lte(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="val",
            threshold=100,
            comparison="lte",
        )
        assert cond.evaluate({"val": 100}) is True
        assert cond.evaluate({"val": 101}) is False

    def test_threshold_eq(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="x",
            threshold=42.0,
            comparison="eq",
        )
        assert cond.evaluate({"x": 42.0}) is True
        assert cond.evaluate({"x": 43.0}) is False

    def test_nested_field_path(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="analytics.reach",
            threshold=1000,
            comparison="gt",
        )
        assert cond.evaluate({"analytics": {"reach": 2000}}) is True
        assert cond.evaluate({"analytics": {"reach": 500}}) is False

    def test_missing_field_returns_false(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="nonexistent.field",
            threshold=10,
            comparison="gt",
        )
        assert cond.evaluate({}) is False

    def test_unknown_condition_type_returns_false(self):
        cond = TriggerCondition(condition_type="unknown_type")
        assert cond.evaluate({}) is False

    def test_non_numeric_value_returns_false(self):
        cond = TriggerCondition(
            condition_type="threshold",
            field_path="val",
            threshold=10,
            comparison="gt",
        )
        assert cond.evaluate({"val": "not_a_number"}) is False


class TestTriggerConfig:
    def test_should_fire_no_conditions(self):
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="test",
            job_task_type="test_task",
        )
        assert trigger.should_fire({}) is True

    def test_should_fire_with_always_condition(self):
        trigger = TriggerConfig(
            trigger_type=TriggerType.CRISIS_DETECTED,
            name="crisis",
            conditions=[TriggerCondition(condition_type="always")],
            job_task_type="crisis",
        )
        assert trigger.should_fire({}) is True

    def test_disabled_trigger_never_fires(self):
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="disabled",
            job_task_type="t",
            enabled=False,
        )
        assert trigger.should_fire({}) is False

    def test_cooldown_prevents_firing(self):
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="cooled",
            job_task_type="t",
            cooldown_seconds=3600,
            last_fired_at=datetime.utcnow(),  # just fired
        )
        assert trigger.should_fire({}) is False

    def test_cooldown_expired_allows_firing(self):
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="ready",
            job_task_type="t",
            cooldown_seconds=1,
            last_fired_at=datetime.utcnow() - timedelta(seconds=5),
        )
        assert trigger.should_fire({}) is True

    def test_all_conditions_must_pass(self):
        trigger = TriggerConfig(
            trigger_type=TriggerType.COST_THRESHOLD_EXCEEDED,
            name="multi_cond",
            conditions=[
                TriggerCondition(condition_type="always"),
                TriggerCondition(
                    condition_type="threshold",
                    field_path="cost",
                    threshold=50,
                    comparison="gt",
                ),
            ],
            job_task_type="alert",
        )
        assert trigger.should_fire({"cost": 100}) is True
        assert trigger.should_fire({"cost": 10}) is False

    def test_trigger_id_generated(self):
        t = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="x",
            job_task_type="y",
        )
        assert t.trigger_id


class TestTriggerFactories:
    def test_cost_exceeded_trigger(self):
        trigger = make_cost_exceeded_trigger(threshold_usd=50.0)
        assert trigger.trigger_type == TriggerType.COST_THRESHOLD_EXCEEDED
        assert trigger.cooldown_seconds == 3600
        assert len(trigger.conditions) == 1
        assert trigger.job_task_type == "cost_alert"

    def test_cost_exceeded_fires_above_threshold(self):
        trigger = make_cost_exceeded_trigger(threshold_usd=50.0)
        assert trigger.should_fire({"session_total_usd": 55.0}) is True
        assert trigger.should_fire({"session_total_usd": 40.0}) is False

    def test_crisis_trigger(self):
        trigger = make_crisis_trigger()
        assert trigger.trigger_type == TriggerType.CRISIS_DETECTED
        assert trigger.job_task_type == "crisis"
        assert trigger.should_fire({}) is True

    def test_all_trigger_types_exist(self):
        expected = [
            "trend_detected",
            "crisis_detected",
            "transfer_detected",
            "match_day_detected",
            "world_cup_detected",
            "breaking_news_detected",
            "revenue_opportunity_detected",
            "governance_issue_detected",
            "cost_threshold_exceeded",
            "audience_drop_detected",
            "sponsor_opportunity_detected",
            "persona_performance_drop",
            "schedule_fired",
            "manual",
        ]
        values = {t.value for t in TriggerType}
        for v in expected:
            assert v in values, f"Missing TriggerType: {v}"
