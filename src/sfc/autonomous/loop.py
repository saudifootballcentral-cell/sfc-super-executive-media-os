"""AutonomousLoop — single-cycle orchestration for the autonomous production loop.

Cycle flow:
  1. Fetch fresh news items from SourceProvider
  2. Filter via DedupStore (skip already-seen headlines within DEDUP_WINDOW_HOURS)
  3. Pick highest-priority item (first item; extensible)
  4. Mark item seen in dedup store before running pipeline
  5. Run MasterOrchestrator pipeline (DRY_RUN or FULL_PIPELINE depending on env)
  6. Read REAL governance result from state.graph_states["main_graph"]["approved_content"]
  7. In live mode: read published Buffer IDs from publishing_connectors_graph
  8. Update LoopMetrics; return result dict

Governance check (step 6) deliberately reads from graph_states, NOT from
state.approval.governance_approved, because the operator_approval stage
unconditionally sets that flag to True in dry_run mode — masking real results.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger("sfc.autonomous.loop")


class AutonomousLoop:
    """Executes one autonomous production cycle end-to-end.

    Exceptions from the pipeline are caught and logged — the caller (scheduler)
    always receives a result dict and never sees an exception from run_cycle().
    """

    def __init__(
        self,
        orchestrator: Any,
        source_provider: Any,
        dedup_store: Any,
        metrics: Any,
    ) -> None:
        self._orchestrator = orchestrator
        self._source = source_provider
        self._dedup = dedup_store
        self._metrics = metrics
        # Read once at construction so the loop reflects Railway Variable state at startup.
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
        self._operator_auto = os.environ.get("OPERATOR_AUTO_APPROVE", "false").lower() == "true"

    async def run_cycle(self) -> dict[str, Any]:
        """Execute one full autonomous cycle. Never raises; always returns a result dict."""
        cycle_start = time.monotonic()
        result: dict[str, Any] = {
            "status": "idle",
            "headline": None,
            "governance_approved": False,
            "published": False,
            "dry_run": not self._live,
            "buffer_ids": [],
            "errors": [],
        }

        try:
            # 1. Record scan tick
            self._metrics.record_scan()
            rss_enabled = os.environ.get("RSS_FEEDS_ENABLED", "false").lower() == "true"
            if rss_enabled:
                from sfc.autonomous.source_provider import get_source_registry
                items = await get_source_registry().get_all_items()
                source_label = "registry"
            else:
                items = await self._source.get_items()
                source_label = self._source.name
            logger.info("[Loop] Cycle start — source=%s total_items=%d", source_label, len(items))

            # 2. Dedup filter (headline + URL)
            fresh = []
            for i in items:
                headline = i.get("headline", "")
                source_url = i.get("source_url", "")
                if self._dedup.is_seen(headline):
                    continue
                if source_url and self._dedup.is_url_seen(source_url):
                    continue
                fresh.append(i)
            deduped_count = len(items) - len(fresh)
            self._metrics.items_deduped += deduped_count
            logger.info(
                "[Loop] Dedup: %d fresh / %d already-seen / store_size=%d",
                len(fresh), deduped_count, self._dedup.size,
            )

            if not fresh:
                result["status"] = "no_new_items"
                logger.info("[Loop] No new items — cycle complete")
                return result

            # 3. Pick item and 4. mark seen immediately (headline + URL)
            item = self._pick_item(fresh)
            headline = item.get("headline", "")
            source_url = item.get("source_url", "")
            result["headline"] = headline[:200]
            self._dedup.mark_seen(headline)
            if source_url:
                self._dedup.mark_url_seen(source_url)

            # 5. Choose workflow mode
            from sfc.orchestration.master_state import WorkflowType
            if self._live and self._operator_auto:
                workflow_type = WorkflowType.FULL_PIPELINE
                dry_run_flag = False
                mode_label = "LIVE"
            else:
                workflow_type = WorkflowType.DRY_RUN
                dry_run_flag = True
                mode_label = "DRY_RUN"

            task_payload: dict[str, Any] = {
                "headline": headline,
                "summary": item.get("summary", ""),
                "source_url": item.get("source_url", ""),
                "tags": item.get("tags", []),
                "category": item.get("category", "news_item"),
                "language": item.get("language", "en"),
            }

            logger.info(
                "[Loop] Running pipeline — mode=%s headline=%r",
                mode_label, headline[:80],
            )

            # 6. Run pipeline through MasterOrchestrator
            state = await self._orchestrator.run(
                task_type=item.get("category", "news_item"),
                task_payload=task_payload,
                workflow_type=workflow_type,
                dry_run=dry_run_flag,
                initiator="autonomous_loop",
                source="autonomous",
            )

            # 7. Check REAL governance from graph_states (not state.approval which is overridden in dry_run)
            main_graph = state.graph_states.get("main_graph", {})
            approved_content = main_graph.get("approved_content", [])
            governance_approved = bool(approved_content)
            result["governance_approved"] = governance_approved

            if not governance_approved:
                self._metrics.items_governance_rejected += 1
                result["status"] = "governance_rejected"
                logger.warning(
                    "[Loop] Governance REJECTED — run_id=%s headline=%r",
                    state.run_id, headline[:80],
                )
                return result

            # 8. Inspect publishing output (live mode only)
            connector_graph = state.graph_states.get("publishing_connectors_graph", {})
            buffer_posts = connector_graph.get("buffer_posts", [])
            if isinstance(buffer_posts, list):
                real_ids = [
                    str(p.get("id") or p.get("buffer_id") or "")
                    for p in buffer_posts
                    if isinstance(p, dict)
                ]
                real_ids = [bid for bid in real_ids if bid and not bid.startswith("dry_")]
            else:
                real_ids = []

            if real_ids:
                result["published"] = True
                result["buffer_ids"] = real_ids
                platform = approved_content[0].get("platform", "x") if approved_content else "x"
                self._metrics.record_publish(buffer_id=real_ids[0], platform=str(platform))
                result["status"] = "published"
                logger.info(
                    "[Loop] PUBLISHED — buffer_ids=%s platform=%s run_id=%s",
                    real_ids, platform, state.run_id,
                )
            else:
                result["status"] = "dry_run_complete" if dry_run_flag else "no_publish_result"

            logger.info(
                "[Loop] Cycle complete — status=%s governance=%s run_id=%s",
                result["status"], governance_approved, state.run_id,
            )

        except Exception as exc:
            self._metrics.record_failure()
            result["status"] = "error"
            result["errors"].append(str(exc))
            logger.error("[Loop] Cycle error: %s", exc, exc_info=True)

        finally:
            duration_ms = (time.monotonic() - cycle_start) * 1000
            self._metrics.last_cycle_duration_ms = duration_ms
            logger.info(
                "[Loop] Duration=%.0fms status=%s",
                duration_ms, result.get("status", "unknown"),
            )

        return result

    def _pick_item(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Select the highest-priority item. Default: first in list (fixture order).

        Future: score by category (match_result > transfer_news > general),
        sentiment_label, and recency.
        """
        return items[0]
