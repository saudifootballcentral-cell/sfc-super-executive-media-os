"""Batch Processing Node — executes batch jobs from the pipeline state."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.batch_processing_node")


async def batch_processing_node(state: SFCState) -> dict[str, Any]:
    """Node: batch_processing_node

    Executes batch jobs defined in the task payload (batch_items list).
    Supports batch intelligence scans, content creation, persona analysis,
    and batch reporting.

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")
    payload = state.get("task_payload", {})
    batch_items = payload.get("batch_items", [])

    logger.info(
        "[BatchProcessing] Starting batch | task=%s items=%d",
        task_type,
        len(batch_items),
    )

    try:
        from sfc.batch.engine import BatchEngine, BatchJob

        engine = BatchEngine(concurrency=3, rate_limit_per_minute=20)

        if not batch_items:
            logger.info("[BatchProcessing] No batch items in payload — skipping")
            return {
                "batch_results": [],
                "pipeline_stage": "batch_skipped",
            }

        jobs = [
            BatchJob(
                task_type=item.get("task_type", task_type),
                payload=item,
                priority=item.get("priority", 5),
            )
            for item in batch_items
        ]

        summary = await engine.run(jobs, batch_name=f"pipeline_batch_{task_type}")
        metrics = engine.get_metrics()

        logger.info(
            "[BatchProcessing] Batch complete | %d/%d succeeded rate=%.1f%%",
            summary.successful,
            summary.total,
            summary.success_rate_pct,
        )

        return {
            "batch_results": [summary.to_dict()],
            "pipeline_stage": "batch_processed",
        }

    except Exception as exc:
        logger.error("[BatchProcessing] Failed (non-fatal): %s", exc)
        return {
            "batch_results": [],
            "pipeline_stage": "batch_failed",
            "warnings": [f"BATCH_PROCESSING_NON_FATAL: {exc}"],
        }
