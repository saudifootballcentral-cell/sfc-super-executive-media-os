"""Memory Update Node — persists all learnings to the hybrid memory architecture."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.memory_update")


async def memory_update_node(state: SFCState) -> dict[str, Any]:
    """Node: memory_update  [FINAL NODE — before END]

    Persists the completed pipeline run across all memory layers:

    - Global Memory     → entities, brand state, analytics summaries
    - Division Memory   → per-division learnings
    - Episodic Memory   → full run record + lessons
    - Knowledge Graph   → new entity/relationship discoveries
    - Working Memory    → cleared (task complete)

    This node is the system's long-term learning loop.
    Package 2+: Will connect to real persistence layer (PostgreSQL / Redis / vector store).
    """
    run_id = state["run_id"]
    task_type = state.get("task_type", "unknown")
    lessons = state.get("lessons_learned", [])
    approved_content = state.get("approved_content", [])
    analytics_report = state.get("analytics_report", {})
    intelligence_report = state.get("intelligence_report", {})
    executive_decision = state.get("executive_decision", {})

    logger.info("[MemoryUpdate] Persisting run %s | %d lessons", run_id, len(lessons))

    updates: list[dict[str, Any]] = []
    completed_at = datetime.utcnow().isoformat()

    try:
        # ----------------------------------------------------------------
        # TODO Package 2: Connect to real persistence layer
        # - GlobalMemory.set() for cross-run context
        # - EpisodicMemory.record() for full episode storage
        # - KnowledgeGraph.add_entity() / .relate() for new discoveries
        # - DivisionMemory updates for per-division learning
        # ----------------------------------------------------------------

        # 1. Episodic memory record
        episode = {
            "memory_type": "episodic",
            "run_id": run_id,
            "task_type": task_type,
            "event": f"{task_type} task processed via full SFC pipeline",
            "decision": executive_decision.get("content_strategy", "Standard pipeline execution"),
            "result": (
                f"Published {len(approved_content)} content item(s). "
                f"Estimated reach: {analytics_report.get('estimated_reach', 0):,}"
            ),
            "lessons": lessons,
            "persisted_at": completed_at,
        }
        updates.append(episode)

        # 2. Global memory — analytics summary
        analytics_update = {
            "memory_type": "global",
            "namespace": "analytics",
            "key": f"run_summary:{run_id}",
            "value": {
                "task_type": task_type,
                "content_count": len(approved_content),
                "estimated_reach": analytics_report.get("estimated_reach", 0),
                "revenue_signals": analytics_report.get("revenue_signal_count", 0),
                "timestamp": completed_at,
            },
        }
        updates.append(analytics_update)

        # 3. Division memory — intelligence findings
        entities = intelligence_report.get("entities_detected", {})
        if any(v for v in entities.values()):
            intel_update = {
                "memory_type": "division",
                "division": "intelligence",
                "key": f"entities:{run_id}",
                "value": entities,
            }
            updates.append(intel_update)

        # 4. Knowledge graph — new entities from this run
        for player in entities.get("players", []):
            updates.append({
                "memory_type": "knowledge_graph",
                "action": "upsert_entity",
                "entity_type": "player",
                "name": player,
            })
        for club in entities.get("clubs", []):
            updates.append({
                "memory_type": "knowledge_graph",
                "action": "upsert_entity",
                "entity_type": "club",
                "name": club,
            })

        # 5. Working memory — clear this run's context
        updates.append({
            "memory_type": "working",
            "action": "clear",
            "run_id": run_id,
        })

        logger.info("[MemoryUpdate] %d update(s) persisted | run_id=%s", len(updates), run_id)

        return {
            "memory_update_log": updates,
            "completed_at": completed_at,
            "pipeline_stage": "complete",
        }

    except Exception as exc:
        logger.error("[MemoryUpdate] Failed: %s", exc)
        return {
            "memory_update_log": [],
            "errors": [f"MEMORY_UPDATE: {exc}"],
            "completed_at": completed_at,
            "pipeline_stage": "complete_with_errors",
        }
