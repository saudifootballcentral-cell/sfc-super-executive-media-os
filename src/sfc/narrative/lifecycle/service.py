"""Narrative Lifecycle Engine — tracks stage progression and health of narratives."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.narrative.lifecycle.models import (
    LifecycleBatch,
    NarrativeHealthMetrics,
    NarrativeLifecycleReport,
    NarrativeStage,
    NarrativeStageTransition,
    STAGE_ORDER,
)

logger = logging.getLogger("sfc.narrative.lifecycle")

_singleton: "NarrativeLifecycleEngine | None" = None


def get_lifecycle_engine() -> "NarrativeLifecycleEngine":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeLifecycleEngine()
    return _singleton


class NarrativeLifecycleEngine:
    """Tracks narrative progression through the 8-stage lifecycle."""

    def __init__(self) -> None:
        self._gateway = None
        self._lifecycle_reports: dict[str, NarrativeLifecycleReport] = {}
        self._history: list[LifecycleBatch] = []
        self._max_history = 200

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def analyze_lifecycle(
        self,
        narrative_id: str,
        narrative_title: str = "",
        context: dict[str, Any] | None = None,
    ) -> NarrativeLifecycleReport:
        """Analyze lifecycle state for a given narrative."""
        context = context or {}
        metrics = self._compute_metrics(context)
        stage = self._determine_stage(metrics, context)
        next_stage = self._predict_next_stage(stage, metrics)
        hours_to_next = self._estimate_hours_to_next_stage(stage, metrics)

        transitions: list[NarrativeStageTransition] = []
        if context.get("previous_stage"):
            try:
                prev = NarrativeStage(context["previous_stage"])
                if prev != stage:
                    transitions.append(NarrativeStageTransition(
                        from_stage=prev,
                        to_stage=stage,
                        trigger=context.get("trigger", "organic growth"),
                        confidence=0.85,
                    ))
            except ValueError:
                pass

        alerts = self._generate_alerts(stage, metrics)
        lifecycle_forecast = await self._get_lifecycle_forecast(narrative_title, stage, metrics)

        report = NarrativeLifecycleReport(
            narrative_id=narrative_id,
            narrative_title=narrative_title,
            current_stage=stage,
            metrics=metrics,
            stage_history=transitions,
            time_in_current_stage_hours=random.uniform(0.5, 48),
            estimated_hours_to_next_stage=hours_to_next,
            next_stage_prediction=next_stage,
            lifecycle_forecast=lifecycle_forecast,
            alerts=alerts,
        )

        self._lifecycle_reports[narrative_id] = report
        return report

    async def batch_analyze(
        self,
        narratives: list[Any],
    ) -> LifecycleBatch:
        """Analyze lifecycle for multiple narratives in batch."""
        reports: list[NarrativeLifecycleReport] = []

        for narrative in narratives[:20]:
            if isinstance(narrative, str):
                report = await self.analyze_lifecycle(narrative_id=narrative)
            else:
                report = await self.analyze_lifecycle(
                    narrative_id=narrative.get("profile_id", narrative.get("narrative_id", "")),
                    narrative_title=narrative.get("title", ""),
                    context=narrative,
                )
            reports.append(report)

        peak_narratives = [r.narrative_id for r in reports if r.current_stage == NarrativeStage.PEAK]
        declining = [r.narrative_id for r in reports if r.current_stage == NarrativeStage.DECLINING]
        emerging = [r.narrative_id for r in reports if r.current_stage == NarrativeStage.EMERGING]

        batch = LifecycleBatch(
            reports=reports,
            peak_narratives=peak_narratives,
            declining_narratives=declining,
            emerging_narratives=emerging,
            total_active=len([r for r in reports if r.current_stage not in (NarrativeStage.DEAD, NarrativeStage.DORMANT)]),
        )

        if len(self._history) < self._max_history:
            self._history.append(batch)

        return batch

    def get_report(self, narrative_id: str) -> NarrativeLifecycleReport | None:
        return self._lifecycle_reports.get(narrative_id)

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [b.to_dict() for b in self._history[-limit:]]

    def _compute_metrics(self, context: dict[str, Any]) -> NarrativeHealthMetrics:
        velocity = context.get("velocity", random.uniform(0.5, 8.0))
        acceleration = context.get("acceleration", random.uniform(-3, 5))
        volume = context.get("volume", random.randint(500, 200000))
        sentiment = context.get("sentiment", random.uniform(-0.5, 0.8))
        reach = context.get("reach", random.randint(5000, 500000))
        influence = context.get("influence", random.uniform(20, 80))

        health_score = min(
            velocity * 8 + max(acceleration, 0) * 5 + influence * 0.3
            + max(sentiment, 0) * 20, 100
        )

        return NarrativeHealthMetrics(
            velocity=round(velocity, 2),
            acceleration=round(acceleration, 2),
            volume=volume,
            influence=round(influence, 1),
            reach=reach,
            sentiment=round(sentiment, 2),
            health_score=round(health_score, 1),
        )

    def _determine_stage(
        self, metrics: NarrativeHealthMetrics, context: dict[str, Any]
    ) -> NarrativeStage:
        score = metrics.health_score
        vel = metrics.velocity
        accel = metrics.acceleration
        vol = metrics.volume

        if score < 10 and vol < 100:
            return NarrativeStage.DEAD
        if score < 20 and vel < 0.5:
            return NarrativeStage.DORMANT
        if score < 30 or (vel > 0 and accel < -2):
            return NarrativeStage.DECLINING
        if score >= 80 and accel >= 0:
            return NarrativeStage.PEAK
        if accel > 3 and vel > 5:
            return NarrativeStage.ACCELERATING
        if vel > 3 and score > 50:
            return NarrativeStage.GROWING
        if vol < 1000 and score < 50:
            return NarrativeStage.SEED
        return NarrativeStage.EMERGING

    def _predict_next_stage(
        self, current: NarrativeStage, metrics: NarrativeHealthMetrics
    ) -> NarrativeStage | None:
        idx = STAGE_ORDER.index(current)
        if metrics.acceleration > 1 and idx < len(STAGE_ORDER) - 1:
            return STAGE_ORDER[idx + 1]
        if metrics.acceleration < -1 and idx > 0:
            return STAGE_ORDER[max(idx - 1, STAGE_ORDER.index(NarrativeStage.DECLINING))]
        return None

    def _estimate_hours_to_next_stage(
        self, stage: NarrativeStage, metrics: NarrativeHealthMetrics
    ) -> float | None:
        if stage in (NarrativeStage.DEAD, NarrativeStage.DORMANT):
            return None
        base = 24 / max(abs(metrics.velocity), 0.1)
        return round(min(base, 72), 1)

    def _generate_alerts(
        self, stage: NarrativeStage, metrics: NarrativeHealthMetrics
    ) -> list[str]:
        alerts = []
        if stage == NarrativeStage.PEAK:
            alerts.append("PEAK ALERT: Narrative at maximum reach — act now")
        if stage == NarrativeStage.ACCELERATING:
            alerts.append("ACCELERATION ALERT: Narrative growing rapidly")
        if metrics.is_at_risk:
            alerts.append("RISK ALERT: Narrative showing negative trajectory")
        if metrics.sentiment < -0.5:
            alerts.append("SENTIMENT ALERT: Highly negative narrative developing")
        return alerts

    async def _get_lifecycle_forecast(
        self, title: str, stage: NarrativeStage, metrics: NarrativeHealthMetrics
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Lifecycle forecast for '{title}' at {stage.value} stage (health={metrics.health_score:.0f})",
                task_type="lifecycle_analysis",
                max_tokens=150,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            return (
                f"Narrative '{title}' is at {stage.value} stage with health score {metrics.health_score:.0f}. "
                f"Expected to {'continue growing' if metrics.acceleration > 0 else 'begin declining'} over the next 24 hours."
            )
