"""Learning integration — feeds analytics data into the LearningEngine and stores to memory."""

from __future__ import annotations

import logging
from typing import Any

from sfc.analytics_sync.aggregation.models import AggregatedPerformance, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.learning")


class LearningIntegration:
    """Bridges the analytics sync layer with the LearningEngine and MemoryManager."""

    async def feed_records(
        self,
        records: list[UnifiedAnalyticsRecord],
        run_id: str = "",
        benchmark_reach: int = 10000,
    ) -> list[Any]:
        """Send analytics to LearningEngineService and return generated lessons."""
        lessons_all: list[Any] = []
        for rec in records:
            if rec.views == 0 and rec.impressions == 0:
                continue  # skip dry-run zeros
            report = {
                "estimated_reach": max(rec.views, rec.impressions),
                "benchmark_reach": benchmark_reach,
                "engagement_rate": rec.engagement_rate,
                "total_revenue_usd": rec.estimated_revenue_usd,
            }
            try:
                from sfc.infrastructure.learning_engine.service import LearningEngineService
                engine = LearningEngineService()
                lessons = await engine.analyze_content_performance(report, run_id)
                lessons_all.extend(lessons)
                logger.debug("[Learning] %d lessons from record %s", len(lessons), rec.record_id)
            except Exception as exc:
                logger.warning("[Learning] Failed to analyze record %s: %s", rec.record_id, exc)
        return lessons_all

    async def store_to_memory(
        self,
        records: list[UnifiedAnalyticsRecord],
        aggregations: dict[str, list[AggregatedPerformance]],
        run_id: str = "",
    ) -> None:
        """Persist analytics to MemoryManagerService via InfrastructureContext."""
        try:
            from sfc.infrastructure.context import get_infrastructure
            memory = get_infrastructure().memory_manager
            await memory.store(
                namespace="analytics_sync",
                key=f"run_{run_id}_records",
                value={
                    "run_id": run_id,
                    "record_count": len(records),
                    "records": [r.to_dict() for r in records[:50]],
                },
                division="analytics",
            )
            for dim, aggs in aggregations.items():
                await memory.store(
                    namespace="analytics_sync",
                    key=f"run_{run_id}_agg_{dim}",
                    value=[a.to_dict() for a in aggs],
                    division="analytics",
                )
            logger.debug("[Learning] Stored %d records + %d aggregation dims to memory", len(records), len(aggregations))
        except Exception as exc:
            logger.warning("[Learning] Memory store failed: %s", exc)

    async def update_knowledge_graph(
        self,
        records: list[UnifiedAnalyticsRecord],
        run_id: str = "",
    ) -> None:
        """Add PerformanceSnapshot entities to the knowledge graph."""
        try:
            from sfc.infrastructure.knowledge_graph.service import get_knowledge_graph
            kg = get_knowledge_graph()
            for rec in records:
                if rec.content_id and rec.views > 0:
                    await kg.add_entity(
                        name=f"perf_{rec.content_id}_{rec.platform.value}",
                        entity_type="content",
                        properties={
                            "content_id": rec.content_id,
                            "platform": rec.platform.value,
                            "views": rec.views,
                            "engagement_rate": rec.engagement_rate,
                            "run_id": run_id,
                        },
                    )
            logger.debug("[Learning] KG updated with %d performance entities", len(records))
        except Exception as exc:
            logger.warning("[Learning] Knowledge graph update failed: %s", exc)


_singleton: LearningIntegration | None = None


def get_learning_integration() -> LearningIntegration:
    global _singleton
    if _singleton is None:
        _singleton = LearningIntegration()
    return _singleton
