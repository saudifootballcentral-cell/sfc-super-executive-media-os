"""Revenue Node — processes revenue signals after analytics.

Sits between analytics and learning in the main pipeline.
Reads revenue_signals populated during planning_node's background phase,
enriches analytics_report with a revenue_summary section, and surfaces
high-value sponsor opportunities for downstream learning.

Does NOT modify governance decisions or content approval status.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.revenue_node")

_HIGH_VALUE_THRESHOLD_USD = 10_000


async def revenue_node(state: SFCState) -> dict[str, Any]:
    """Node: revenue_node

    Processes revenue signals from the planning phase and enriches the
    analytics report with a structured revenue_summary. Flags high-value
    sponsor opportunities for the learning and memory nodes.
    """
    signals: list[dict[str, Any]] = state.get("revenue_signals", [])
    analytics_report: dict[str, Any] = state.get("analytics_report", {})
    task_type = state.get("task_type", "")
    approved_content = state.get("approved_content", [])

    logger.info(
        "[RevenueNode] Processing %d revenue signal(s) | task=%s | published=%d",
        len(signals),
        task_type,
        len(approved_content),
    )

    try:
        if not signals:
            revenue_summary: dict[str, Any] = {
                "total_opportunity_usd": 0,
                "signal_count": 0,
                "high_value_signals": 0,
                "priority_brand": None,
                "sponsor_categories": [],
                "activation_ready": False,
                "processed_at": datetime.utcnow().isoformat(),
            }
        else:
            total_value = sum(s.get("estimated_value_usd", 0) for s in signals)
            high_value = [
                s for s in signals
                if s.get("estimated_value_usd", 0) >= _HIGH_VALUE_THRESHOLD_USD
            ]

            # Group by category
            categories: dict[str, float] = {}
            for s in signals:
                cat = s.get("category", "unknown")
                categories[cat] = categories.get(cat, 0) + s.get("estimated_value_usd", 0)

            # Sort brands by value
            sorted_signals = sorted(signals, key=lambda x: x.get("estimated_value_usd", 0), reverse=True)
            priority_brand = sorted_signals[0].get("brand") if sorted_signals else None

            revenue_summary = {
                "total_opportunity_usd": total_value,
                "signal_count": len(signals),
                "high_value_signals": len(high_value),
                "priority_brand": priority_brand,
                "sponsor_categories": list(categories.keys()),
                "category_breakdown_usd": categories,
                "top_signals": [
                    {
                        "brand": s.get("brand"),
                        "category": s.get("category"),
                        "estimated_value_usd": s.get("estimated_value_usd"),
                        "activation_type": s.get("activation_type"),
                    }
                    for s in sorted_signals[:3]
                ],
                "activation_ready": bool(high_value),
                "processed_at": datetime.utcnow().isoformat(),
            }

        # Package 7: AI prioritizes revenue signals and identifies highest-value opportunities
        ai_revenue_insights: dict[str, Any] = {}
        try:
            from sfc.ai.model_gateway import get_ai_gateway
            from sfc.ai.models import ModelRequest
            from sfc.ai.prompt_loader import get_prompt_loader
            import json as _json

            loader = get_prompt_loader()
            system_prompt = loader.load("divisions", "revenue")
            gateway = get_ai_gateway()
            ai_request = ModelRequest(
                task_type="revenue",
                system_prompt=system_prompt,
                user_message=(
                    f"Analyze revenue signals and prioritize opportunities:\n"
                    f"task_type={task_type}\n"
                    f"revenue_summary={_json.dumps(revenue_summary)}\n"
                    f"published_content_count={len(approved_content)}\n\n"
                    "Return JSON: {\"revenue_insights\": str, \"top_opportunities\": list[str], "
                    "\"priority_actions\": list[str]}"
                ),
                max_tokens=512,
                json_mode=True,
            )
            ai_response = await gateway.complete(ai_request)
            if ai_response.success and ai_response.parsed and not ai_response.used_fallback:
                ai_revenue_insights = ai_response.parsed
                logger.debug("[RevenueNode] AI revenue insights generated")
        except Exception as ai_exc:
            logger.debug("[RevenueNode] AI insights skipped: %s", ai_exc)

        if ai_revenue_insights:
            revenue_summary["ai_insights"] = ai_revenue_insights

        enriched_analytics = {
            **analytics_report,
            "revenue_summary": revenue_summary,
        }

        logger.info(
            "[RevenueNode] Revenue processed | total=$%.0f | high_value=%d",
            revenue_summary.get("total_opportunity_usd", 0),
            revenue_summary.get("high_value_signals", 0),
        )

        return {
            "analytics_report": enriched_analytics,
            "pipeline_stage": "revenue_processed",
        }

    except Exception as exc:
        logger.error("[RevenueNode] Failed (non-fatal): %s", exc)
        return {
            "pipeline_stage": "revenue_processed",
            "warnings": [f"REVENUE_NODE_NON_FATAL: {exc}"],
        }
