"""Autonomous Trigger Engine — detects signals and fires workflows automatically.

Monitors system state (analytics, costs, personas, governance) and fires
JobDefinitions when threshold conditions are met.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from sfc.scheduler.triggers import TriggerConfig, TriggerType

logger = logging.getLogger("sfc.autonomous.trigger_engine")


class TriggerEvent(BaseModel):
    """A fired trigger event record."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger_type: TriggerType
    trigger_name: str
    fired_at: datetime = Field(default_factory=datetime.utcnow)
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    resulting_job_id: str | None = None
    alert_sent: bool = False
    acknowledged: bool = False

    model_config = {"frozen": False}


class AutonomousTriggerEngine:
    """Evaluates signals and fires autonomous workflows when conditions are met."""

    def __init__(self) -> None:
        self._triggers: list[TriggerConfig] = self._build_default_triggers()
        self._fired_events: list[TriggerEvent] = []

    def _build_default_triggers(self) -> list[TriggerConfig]:
        from sfc.scheduler.triggers import (
            TriggerCondition,
            make_cost_exceeded_trigger,
            make_crisis_trigger,
        )
        return [
            make_cost_exceeded_trigger(threshold_usd=50.0),
            make_crisis_trigger(),
            TriggerConfig(
                trigger_type=TriggerType.AUDIENCE_DROP_DETECTED,
                name="audience_drop_15pct",
                conditions=[
                    TriggerCondition(
                        condition_type="threshold",
                        field_path="analytics_report.estimated_reach",
                        threshold=10_000,
                        comparison="lt",
                    )
                ],
                job_task_type="audience_recovery",
                job_payload={"auto_triggered": True},
                cooldown_seconds=3600,
            ),
            TriggerConfig(
                trigger_type=TriggerType.REVENUE_OPPORTUNITY_DETECTED,
                name="high_value_sponsor",
                conditions=[
                    TriggerCondition(
                        condition_type="threshold",
                        field_path="revenue_summary.total_opportunity_usd",
                        threshold=10_000,
                        comparison="gte",
                    )
                ],
                job_task_type="sponsor_activation",
                job_payload={"auto_triggered": True, "priority": "high"},
                cooldown_seconds=1800,
            ),
        ]

    def add_trigger(self, trigger: TriggerConfig) -> str:
        self._triggers.append(trigger)
        return trigger.trigger_id

    def remove_trigger(self, trigger_id: str) -> bool:
        before = len(self._triggers)
        self._triggers = [t for t in self._triggers if t.trigger_id != trigger_id]
        return len(self._triggers) < before

    async def evaluate(self, context: dict[str, Any]) -> list[TriggerEvent]:
        """Evaluate all triggers against current context. Returns fired events."""
        fired: list[TriggerEvent] = []
        for trigger in self._triggers:
            if not trigger.should_fire(context):
                continue
            event = TriggerEvent(
                trigger_type=trigger.trigger_type,
                trigger_name=trigger.name,
                context_snapshot=self._sanitize_context(context),
            )
            trigger.last_fired_at = datetime.utcnow()
            self._fired_events.append(event)
            fired.append(event)
            logger.info(
                "[TriggerEngine] Fired: %s (type=%s)",
                trigger.name,
                trigger.trigger_type.value,
            )
        return fired

    async def evaluate_from_state(self, pipeline_state: dict[str, Any]) -> list[TriggerEvent]:
        """Evaluate triggers from an SFCState dict (flattened context)."""
        context = self._flatten_state(pipeline_state)
        return await self.evaluate(context)

    def _flatten_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract key metrics from pipeline state into a flat context dict."""
        analytics = state.get("analytics_report", {})
        revenue = analytics.get("revenue_summary", {})
        return {
            "analytics_report": analytics,
            "revenue_summary": revenue,
            "session_total_usd": self._get_cost_total(),
            "errors": state.get("errors", []),
            "governance_rejections": len(state.get("rejected_content", [])),
            "task_type": state.get("task_type", ""),
        }

    def _get_cost_total(self) -> float:
        try:
            from sfc.ai.cost_tracker import get_cost_tracker
            return get_cost_tracker().session_total_usd
        except Exception:
            return 0.0

    def _sanitize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for k, v in context.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                safe[k] = v
            elif isinstance(v, dict):
                safe[k] = {sk: sv for sk, sv in v.items() if isinstance(sv, (str, int, float, bool, type(None)))}
            elif isinstance(v, list):
                safe[k] = v[:5]
        return safe

    def get_fired_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.model_dump(mode="json") for e in self._fired_events[-limit:]]

    def get_trigger_report(self) -> dict[str, Any]:
        return {
            "total_triggers": len(self._triggers),
            "enabled_triggers": sum(1 for t in self._triggers if t.enabled),
            "total_fired": len(self._fired_events),
            "triggers": [
                {
                    "trigger_id": t.trigger_id,
                    "name": t.name,
                    "type": t.trigger_type.value,
                    "enabled": t.enabled,
                    "cooldown_seconds": t.cooldown_seconds,
                    "last_fired_at": t.last_fired_at.isoformat() if t.last_fired_at else None,
                }
                for t in self._triggers
            ],
        }
