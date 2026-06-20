"""Revenue Background Node — parallel sponsor and monetization scanning.

Runs in PARALLEL with intelligence and analytics_background.
Results stored in state; consumed by publishing (for ad integration) and analytics (final).

Package 2: RevenueDivision will replace the stub logic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.revenue")

_CATEGORY_OPPORTUNITIES: dict[str, list[dict[str, Any]]] = {
    "transfer": [
        {"brand": "SportsPesa", "category": "sports_betting", "estimated_value_usd": 25_000},
        {"brand": "Noon Sports", "category": "streaming", "estimated_value_usd": 15_000},
    ],
    "match": [
        {"brand": "STC Sport", "category": "telecom", "estimated_value_usd": 18_000},
        {"brand": "Al Rajhi Bank", "category": "finance", "estimated_value_usd": 12_000},
    ],
    "campaign": [
        {"brand": "adidas", "category": "sportswear", "estimated_value_usd": 50_000},
        {"brand": "Pepsi KSA", "category": "fmcg", "estimated_value_usd": 35_000},
    ],
}


async def revenue_background_node(state: SFCState) -> dict[str, Any]:
    """Node: revenue_background  [PARALLEL PHASE — independent]

    Runs simultaneously with intelligence and analytics_background.
    Scans for sponsor integration opportunities, ad slots, and revenue signals
    relevant to this content run.

    Responsibilities:
    - Match content to active sponsor categories
    - Identify ad placement opportunities
    - Surface partnership signals
    - Flag premium content monetization potential

    Package 2: RevenueDivision.background_scan()
    """
    task_type = state.get("task_type", "news")
    plan = state.get("execution_plan", {})
    payload = state.get("task_payload", {})

    logger.info("[Revenue:Background] Scanning for opportunities | task=%s", task_type)

    try:
        # ----------------------------------------------------------------
        # TODO Package 2: Replace with RevenueDivision.background_scan()
        # - Query active sponsor contracts
        # - Match task to sponsor activation triggers
        # - Calculate CPM/CPC estimates per platform
        # - Flag YouTube monetization eligibility
        # ----------------------------------------------------------------

        opportunities = _CATEGORY_OPPORTUNITIES.get(task_type, [])
        revenue_opportunity_flag = plan.get("revenue_opportunity", False)

        if not revenue_opportunity_flag and not opportunities:
            logger.info("[Revenue:Background] No revenue signals for task_type=%s", task_type)
            return {"revenue_signals": []}

        signals: list[dict[str, Any]] = []
        for opp in opportunities:
            signal = {
                **opp,
                "activation_type": "sponsored_content",
                "platforms": plan.get("platforms_targeted", [])[:3],
                "detected_at": datetime.utcnow().isoformat(),
                "status": "opportunity",
            }
            signals.append(signal)

        # Platform ad revenue estimate
        if "youtube" in plan.get("platforms_targeted", []):
            signals.append({
                "brand": "YouTube AdSense",
                "category": "platform_ads",
                "estimated_value_usd": 500,
                "activation_type": "ad_revenue",
                "platforms": ["youtube"],
                "detected_at": datetime.utcnow().isoformat(),
                "status": "automatic",
            })

        total_value = sum(s.get("estimated_value_usd", 0) for s in signals)
        logger.info(
            "[Revenue:Background] Found %d signal(s) | est. value=$%.0f",
            len(signals),
            total_value,
        )

        return {"revenue_signals": signals}

    except Exception as exc:
        logger.error("[Revenue:Background] Failed: %s", exc)
        return {
            "revenue_signals": [],
            "errors": [f"REVENUE_BACKGROUND: {exc}"],
        }
