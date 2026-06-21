"""Scheduler trigger types and conditions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    TREND_DETECTED = "trend_detected"
    CRISIS_DETECTED = "crisis_detected"
    TRANSFER_DETECTED = "transfer_detected"
    MATCH_DAY_DETECTED = "match_day_detected"
    WORLD_CUP_DETECTED = "world_cup_detected"
    BREAKING_NEWS_DETECTED = "breaking_news_detected"
    REVENUE_OPPORTUNITY_DETECTED = "revenue_opportunity_detected"
    GOVERNANCE_ISSUE_DETECTED = "governance_issue_detected"
    COST_THRESHOLD_EXCEEDED = "cost_threshold_exceeded"
    AUDIENCE_DROP_DETECTED = "audience_drop_detected"
    SPONSOR_OPPORTUNITY_DETECTED = "sponsor_opportunity_detected"
    PERSONA_PERFORMANCE_DROP = "persona_performance_drop"
    SCHEDULE_FIRED = "schedule_fired"
    MANUAL = "manual"


class TriggerCondition(BaseModel):
    """Condition that must be true for a trigger to fire."""

    condition_type: str
    threshold: float | None = None
    comparison: str = "gt"  # gt, lt, eq, gte, lte
    field_path: str = ""
    value: Any = None

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate condition against a context dict."""
        if self.condition_type == "always":
            return True
        if self.condition_type == "threshold":
            val = self._get_nested(context, self.field_path)
            if val is None or self.threshold is None:
                return False
            try:
                v = float(val)
                t = float(self.threshold)
            except (TypeError, ValueError):
                return False
            return {
                "gt": v > t, "lt": v < t, "eq": v == t,
                "gte": v >= t, "lte": v <= t,
            }.get(self.comparison, False)
        return False

    def _get_nested(self, d: dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        cur: Any = d
        for p in parts:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(p)
        return cur


class TriggerConfig(BaseModel):
    """Configuration for an event-based trigger."""

    trigger_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger_type: TriggerType
    name: str
    conditions: list[TriggerCondition] = Field(default_factory=list)
    job_task_type: str
    job_payload: dict[str, Any] = Field(default_factory=dict)
    cooldown_seconds: int = 300
    enabled: bool = True
    last_fired_at: datetime | None = None

    def should_fire(self, context: dict[str, Any]) -> bool:
        """Check if all conditions are met and cooldown has passed."""
        if not self.enabled:
            return False
        if self.last_fired_at is not None:
            elapsed = (datetime.utcnow() - self.last_fired_at).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False
        return all(c.evaluate(context) for c in self.conditions) if self.conditions else True


# Pre-built trigger factory helpers
def make_cost_exceeded_trigger(threshold_usd: float = 50.0) -> TriggerConfig:
    return TriggerConfig(
        trigger_type=TriggerType.COST_THRESHOLD_EXCEEDED,
        name="daily_cost_exceeded",
        conditions=[
            TriggerCondition(
                condition_type="threshold",
                field_path="session_total_usd",
                threshold=threshold_usd,
                comparison="gte",
            )
        ],
        job_task_type="cost_alert",
        job_payload={"threshold_usd": threshold_usd, "auto_alert": True},
        cooldown_seconds=3600,
    )


def make_crisis_trigger() -> TriggerConfig:
    return TriggerConfig(
        trigger_type=TriggerType.CRISIS_DETECTED,
        name="crisis_auto_trigger",
        conditions=[TriggerCondition(condition_type="always")],
        job_task_type="crisis",
        job_payload={"auto_triggered": True, "war_room": "crisis"},
        cooldown_seconds=600,
    )
