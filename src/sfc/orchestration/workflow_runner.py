"""WorkflowRunner — executes a multi-stage workflow using the ExecutionPlan."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.events.types import (
    DataIngestionCompleted,
    DryRunCompleted,
    OrchestrationAborted,
    OrchestrationCompleted,
    OrchestrationFailed,
    OrchestrationStarted,
    StageCompleted,
    StageFailed,
    StageSkipped,
    StageStarted,
)
from sfc.orchestration.approval_gate import ApprovalDeniedError
from sfc.orchestration.graph_bridge import GraphBridge, GraphBridgeError
from sfc.orchestration.master_state import RunStatus, StageStatus
from sfc.orchestration.run_context import RunContext


class WorkflowRunner:
    """Drives an ExecutionPlan to completion, stage by stage.

    Each stage:
      1. Marks the stage as started in MasterState
      2. Fires StageStarted event on the EventBus
      3. Executes the stage (either graph.ainvoke() via GraphBridge, or built-in logic)
      4. Marks the stage as completed / failed / skipped
      5. Fires StageCompleted / StageFailed / StageSkipped event
      6. Checkpoints MasterState

    Recovery: on failure, delegates to RecoveryEngine for retry or abort.
    """

    def __init__(self, bridge: GraphBridge | None = None) -> None:
        self._bridge = bridge or GraphBridge()

    async def run(self, ctx: RunContext) -> None:
        """Execute all stages in ctx.plan.  Mutates ctx.state throughout."""
        bus = get_event_bus()
        state = ctx.state
        plan = ctx.plan

        state.status = RunStatus.RUNNING
        state.started_at = datetime.utcnow()
        state.append_history("orchestration_started")
        bus.publish(
            OrchestrationStarted(
                division="orchestration",
                run_id=state.run_id,
                payload={"workflow_type": state.workflow_type.value, "dry_run": state.dry_run},
            )
        )
        await ctx.checkpoint()

        from sfc.orchestration.recovery import RecoveryEngine
        recovery = RecoveryEngine(max_retries=2, base_backoff_seconds=0.5)

        try:
            for stage in plan.stages:
                await self._run_stage(stage, ctx, recovery)
                if state.status in (RunStatus.FAILED, RunStatus.ABORTED):
                    break

        except Exception as exc:
            state.status = RunStatus.FAILED
            state.errors.append(f"Unhandled orchestration error: {exc}")
            state.append_history("orchestration_failed", {"error": str(exc)})
            bus.publish(
                OrchestrationFailed(
                    division="orchestration",
                    run_id=state.run_id,
                    payload={"error": str(exc)},
                    priority="high",
                )
            )
            await ctx.checkpoint()
            return

        state.completed_at = datetime.utcnow()

        if state.status not in (RunStatus.FAILED, RunStatus.ABORTED):
            if state.dry_run:
                state.status = RunStatus.COMPLETED
                bus.publish(
                    DryRunCompleted(
                        division="orchestration",
                        run_id=state.run_id,
                        payload=state.to_summary(),
                    )
                )
            else:
                state.status = RunStatus.COMPLETED
                bus.publish(
                    OrchestrationCompleted(
                        division="orchestration",
                        run_id=state.run_id,
                        payload=state.to_summary(),
                    )
                )

        state.append_history("orchestration_finished", {"status": state.status.value})
        await ctx.checkpoint()

    # ------------------------------------------------------------------
    # Stage dispatcher
    # ------------------------------------------------------------------

    async def _run_stage(
        self,
        stage: Any,
        ctx: RunContext,
        recovery: Any,
    ) -> None:
        bus = get_event_bus()
        state = ctx.state
        stage_name = stage.name

        # Skip publishing stage in dry run
        if ctx.plan.is_skippable(stage_name):
            state.mark_stage_skipped(stage_name, reason="dry_run_mode")
            ctx.audit.log_stage_skip(stage_name, "dry_run_mode")
            bus.publish(
                StageSkipped(
                    division="orchestration",
                    run_id=state.run_id,
                    payload={"stage": stage_name, "reason": "dry_run_mode"},
                )
            )
            await ctx.checkpoint()
            return

        state.mark_stage_started(stage_name)
        ctx.audit.log_stage_start(stage_name)
        bus.publish(
            StageStarted(
                division="orchestration",
                run_id=state.run_id,
                payload={"stage": stage_name},
            )
        )

        try:
            await self._dispatch_stage(stage, ctx)
            state.mark_stage_completed(stage_name)
            rec = state.stages.get(stage_name)
            duration_ms = rec.duration_ms if rec else 0.0
            ctx.audit.log_stage_complete(stage_name, duration_ms)
            bus.publish(
                StageCompleted(
                    division="orchestration",
                    run_id=state.run_id,
                    payload={
                        "stage": stage_name,
                        "workflow_type": state.workflow_type.value,
                        "duration_ms": duration_ms,
                        "status": "completed",
                        "output_summary": self._stage_output_summary(stage_name, ctx),
                    },
                )
            )
            await ctx.checkpoint()

        except ApprovalDeniedError as exc:
            # Hard stop — no retry on approval failures
            state.mark_stage_failed(stage_name, str(exc))
            ctx.audit.log_stage_fail(stage_name, str(exc))
            state.status = RunStatus.ABORTED
            bus.publish(
                OrchestrationAborted(
                    division="orchestration",
                    run_id=state.run_id,
                    payload={"stage": stage_name, "reason": str(exc)},
                    priority="high",
                )
            )
            await ctx.checkpoint()

        except Exception as exc:
            if recovery.can_retry(stage_name):
                result = await recovery.attempt_retry(stage_name, lambda: self._dispatch_stage(stage, ctx))
                if result.success:
                    state.mark_stage_completed(stage_name, artifacts={"recovered": True})
                    ctx.audit.log_recovery(stage_name, "retry", recovery.retry_counts().get(stage_name, 0))
                    return
            # Retries exhausted or unretryable
            state.mark_stage_failed(stage_name, str(exc))
            ctx.audit.log_stage_fail(stage_name, str(exc))
            bus.publish(
                StageFailed(
                    division="orchestration",
                    run_id=state.run_id,
                    payload={"stage": stage_name, "error": str(exc)},
                    priority="high",
                )
            )
            if stage.required:
                state.status = RunStatus.FAILED
                bus.publish(
                    OrchestrationFailed(
                        division="orchestration",
                        run_id=state.run_id,
                        payload={"stage": stage_name, "error": str(exc)},
                        priority="high",
                    )
                )
            await ctx.checkpoint()

    # ------------------------------------------------------------------
    # Stage dispatch table
    # ------------------------------------------------------------------

    async def _dispatch_stage(self, stage: Any, ctx: RunContext) -> None:
        dispatch = {
            "data_ingestion": self._stage_data_ingestion,
            "governance_gate": self._stage_governance_gate,
            "operator_approval": self._stage_operator_approval,
            "analytics": self._stage_analytics,
            "reporting": self._stage_reporting,
        }
        handler = dispatch.get(stage.name)
        if handler:
            await handler(ctx)
        elif stage.graph and stage.graph != "builtin":
            await self._stage_run_graph(stage.graph, ctx)
        else:
            raise RuntimeError(f"No handler for stage '{stage.name}'")

    # ------------------------------------------------------------------
    # Output summary builder (payload for StageCompleted)
    # ------------------------------------------------------------------

    def _stage_output_summary(self, stage_name: str, ctx: RunContext) -> dict[str, Any]:
        """Return a compact summary of what the stage produced."""
        state = ctx.state
        graph_key_map = {
            "social_intelligence": "social_intelligence_graph",
            "main_pipeline": "main_graph",
            "creative_production": "creative_production_graph",
            "publishing": "publishing_connectors_graph",
        }
        graph_key = graph_key_map.get(stage_name)
        if graph_key:
            gs = state.graph_states.get(graph_key, {})
            return {
                "approved_content_count": len(gs.get("approved_content", [])),
                "error_count": len(gs.get("errors", [])),
            }
        rec = state.stages.get(stage_name)
        return {"artifacts": list(rec.artifacts.keys()) if rec and rec.artifacts else []}

    # ------------------------------------------------------------------
    # Builtin stage implementations
    # ------------------------------------------------------------------

    async def _stage_data_ingestion(self, ctx: RunContext) -> None:
        """Warm the Package 10A fixture/provider cache."""
        from sfc.data.fixtures.loader import get_fixture_loader
        loader = get_fixture_loader()
        # Touch all fixture collections to prime the cache
        loader.get_trends()
        loader.get_topic_scores()
        loader.get_news_items()
        bus = get_event_bus()
        bus.publish(
            DataIngestionCompleted(
                division="data",
                run_id=ctx.run_id,
                payload={"source": "mock_fixture", "items_loaded": "all"},
            )
        )

    async def _stage_governance_gate(self, ctx: RunContext) -> None:
        """Extract governance result from main_pipeline graph state."""
        main_state = ctx.state.graph_states.get("main_graph", {})
        governance_reviews = main_state.get("governance_reviews", [])
        approved_content = main_state.get("approved_content", [])

        governance_approved = len(approved_content) > 0 or len(governance_reviews) > 0
        ctx.gate.set_governance_approved(ctx.state, governance_approved)
        ctx.audit.log_governance(
            decision="approved" if governance_approved else "no_content",
            content_count=len(approved_content),
            rejected_count=len(main_state.get("rejected_content", [])),
        )
        ctx.state.add_decision(
            "governance_gate",
            "approved" if governance_approved else "no_publishable_content",
            {"approved_count": len(approved_content)},
        )

    async def _stage_operator_approval(self, ctx: RunContext) -> None:
        """In dry-run or auto-approve mode, grant approval programmatically."""
        if ctx.dry_run:
            # Dry run: mark governance check done but skip actual publish lock
            ctx.gate.set_governance_approved(ctx.state, True)
            return

        # In a real deployment, this stage would pause and wait for a webhook/API call.
        # For now, auto-approve when OPERATOR_AUTO_APPROVE=true (test/staging only).
        import os
        auto = os.environ.get("OPERATOR_AUTO_APPROVE", "false").lower() == "true"
        if auto:
            ctx.gate.grant_operator_approval(ctx.state, granted_by="auto_approve", reason="OPERATOR_AUTO_APPROVE=true")
        else:
            ctx.state.status = RunStatus.AWAITING_APPROVAL
            from sfc.events.types import OperatorApprovalRequested
            get_event_bus().publish(
                OperatorApprovalRequested(
                    division="orchestration",
                    run_id=ctx.run_id,
                    payload={"run_id": ctx.run_id},
                    priority="high",
                )
            )
            # Raise so the run pauses here — caller must call grant_operator_approval()
            from sfc.orchestration.approval_gate import ApprovalDeniedError
            raise ApprovalDeniedError("Awaiting human operator approval — call grant_operator_approval()")

    async def _stage_analytics(self, ctx: RunContext) -> None:
        """Aggregate post-publish analytics from connector graph state."""
        connector_state = ctx.state.graph_states.get("publishing_connectors_graph", {})
        analytics_data = connector_state.get("analytics_data", {})
        ctx.state.artifacts["analytics"] = analytics_data

    async def _stage_reporting(self, ctx: RunContext) -> None:
        """Collect reporting artifacts from all graph runs."""
        artifacts: dict[str, Any] = {
            "social_intelligence": bool(ctx.state.graph_states.get("social_intelligence_graph")),
            "main_pipeline": bool(ctx.state.graph_states.get("main_graph")),
            "creative_production": bool(ctx.state.graph_states.get("creative_production_graph")),
            "publishing": bool(ctx.state.graph_states.get("publishing_connectors_graph")),
        }
        ctx.state.artifacts["reporting_summary"] = artifacts

    # ------------------------------------------------------------------
    # Graph execution via bridge
    # ------------------------------------------------------------------

    async def _stage_run_graph(self, graph_name: str, ctx: RunContext) -> None:
        state = ctx.state
        prior = {}
        # Thread social intelligence output into the main pipeline
        if graph_name == "main_graph":
            si_state = state.graph_states.get("social_intelligence_graph", {})
            prior = {
                "social_intelligence_report": si_state.get("social_intelligence_report", {}),
                "trend_radar_data": si_state.get("trend_radar_data", {}),
                "narrative_intelligence_data": si_state.get("narrative_intelligence_data", {}),
                "fan_sentiment_data": si_state.get("fan_sentiment_data", {}),
            }

        result = await self._bridge.execute(
            graph_name=graph_name,
            run_id=state.run_id,
            task_type=state.task_type,
            task_payload=state.task_payload,
            prior_state=prior if prior else None,
        )
        state.graph_states[graph_name] = result

        # Propagate warnings/errors from graph state to master state
        for w in result.get("warnings", []):
            state.warnings.append(f"[{graph_name}] {w}")
        for e in result.get("errors", []):
            state.errors.append(f"[{graph_name}] {e}")
