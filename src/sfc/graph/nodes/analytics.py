"""Analytics Nodes — background phase (parallel) + final join node.

analytics_background_node: runs in PARALLEL with intelligence and revenue_background.
    Processes historical performance data while intelligence does research.

analytics_node: the JOIN node — waits for publishing + analytics_background + revenue_background.
    Combines all analytics data into the final report.

Package 2: AnalyticsDivision will replace the stub logic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.analytics")


# ---------------------------------------------------------------------------
# Background node (PARALLEL PHASE)
# ---------------------------------------------------------------------------

async def analytics_background_node(state: SFCState) -> dict[str, Any]:
    """Node: analytics_background  [PARALLEL PHASE — independent]

    Runs simultaneously with intelligence and revenue_background.
    Processes historical performance benchmarks without blocking the main chain.

    Responsibilities:
    - Load historical content performance
    - Calculate platform benchmarks
    - Identify top-performing content patterns
    - Provide context for final analytics comparison

    Package 2: AnalyticsDivision.background_analysis()
    """
    task_type = state.get("task_type", "news")
    plan = state.get("execution_plan", {})

    logger.info("[Analytics:Background] Starting historical analysis | task=%s", task_type)

    try:
        # ----------------------------------------------------------------
        # TODO Package 2: Replace with AnalyticsDivision.background_analysis()
        # - Query historical content DB
        # - Calculate 7/30/90-day benchmarks per platform
        # - Identify top content patterns for this task type
        # ----------------------------------------------------------------

        platforms = plan.get("platforms_targeted", [])
        background_data: dict[str, Any] = {
            "analysis_type": "historical_benchmark",
            "task_type": task_type,
            "benchmarks": _generate_benchmarks(platforms, task_type),
            "top_performing_content_patterns": _top_patterns(task_type),
            "optimal_publish_times": _optimal_times(platforms),
            "audience_insights": {
                "primary_demographic": "18-34 Saudi football fans",
                "peak_engagement_day": "Friday",
                "peak_engagement_hour_utc": 19,
            },
            "analysed_at": datetime.utcnow().isoformat(),
        }

        logger.info("[Analytics:Background] Historical analysis complete")
        return {"analytics_background_data": background_data}

    except Exception as exc:
        logger.error("[Analytics:Background] Failed: %s", exc)
        return {
            "analytics_background_data": {"error": str(exc), "analysis_type": "failed"},
            "errors": [f"ANALYTICS_BACKGROUND: {exc}"],
        }


# ---------------------------------------------------------------------------
# Final analytics node (JOIN)
# ---------------------------------------------------------------------------

async def analytics_node(state: SFCState) -> dict[str, Any]:
    """Node: analytics  [JOIN — waits for publishing + analytics_background + revenue_background]

    This is the convergence point for all three parallel branches.
    Combines publishing results with background analytics and revenue signals
    to produce the final performance report.

    Responsibilities:
    - Aggregate reach, engagement, watch time
    - Compare vs historical benchmarks
    - Calculate ROI
    - Identify optimisation opportunities

    Package 2: AnalyticsDivision.final_report()
    """
    publish_results = state.get("publish_results", {})
    background = state.get("analytics_background_data", {})
    revenue_signals = state.get("revenue_signals", [])
    plan = state.get("execution_plan", {})
    approved_content = state.get("approved_content", [])

    logger.info("[Analytics:Final] Generating analytics report | published=%d", len(approved_content))

    try:
        # ----------------------------------------------------------------
        # TODO Package 2: Replace with AnalyticsDivision.final_report()
        # - Real platform metrics via APIs (TikTok, Instagram, YouTube, etc.)
        # - Attribution modeling
        # - Cohort analysis
        # ----------------------------------------------------------------

        benchmarks = background.get("benchmarks", {})
        kpi_targets = plan.get("kpi_targets", {})
        content_count = len(approved_content)

        report: dict[str, Any] = {
            "run_id": state["run_id"],
            "content_pieces_published": content_count,
            "platforms_reached": list(publish_results.get("platform_results", {}).keys()),
            "estimated_reach": _estimate_reach(content_count, plan),
            "estimated_engagement_rate": _estimate_engagement(plan.get("task_type", "")),
            "estimated_watch_time_minutes": _estimate_watch_time(content_count),
            "kpi_vs_target": _compare_kpis(
                content_count,
                kpi_targets,
                plan.get("task_type", ""),
            ),
            "benchmark_comparison": benchmarks,
            "revenue_signal_count": len(revenue_signals),
            "estimated_revenue_impact_usd": sum(
                s.get("estimated_value_usd", 0) for s in revenue_signals
            ),
            "optimisation_recommendations": _generate_recommendations(plan, background),
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "[Analytics:Final] Report ready | est_reach=%d revenue_signals=%d",
            report["estimated_reach"],
            report["revenue_signal_count"],
        )

        return {
            "analytics_report": report,
            "pipeline_stage": "analytics_complete",
        }

    except Exception as exc:
        logger.error("[Analytics:Final] Failed: %s", exc)
        return {
            "analytics_report": {"error": str(exc)},
            "errors": [f"ANALYTICS_FINAL: {exc}"],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_benchmarks(platforms: list[str], task_type: str) -> dict[str, Any]:
    benchmarks: dict[str, Any] = {}
    for platform in platforms:
        benchmarks[platform] = {
            "avg_reach_30d": {"tiktok": 80000, "instagram_reels": 45000}.get(platform, 20000),
            "avg_engagement": {"tiktok": 0.07, "instagram_reels": 0.05}.get(platform, 0.03),
        }
    return benchmarks


def _top_patterns(task_type: str) -> list[str]:
    patterns: dict[str, list[str]] = {
        "transfer": ["player reveal video", "wage comparison graphic", "reaction thread"],
        "match": ["highlight reel", "tactical breakdown", "player ratings"],
        "news": ["breaking header", "context thread", "reaction poll"],
    }
    return patterns.get(task_type, ["standard content"])


def _optimal_times(platforms: list[str]) -> dict[str, str]:
    return {p: "19:00 UTC" for p in platforms}


def _estimate_reach(content_count: int, plan: dict[str, Any]) -> int:
    base = {"news": 50000, "match": 200000, "transfer": 500000}.get(plan.get("task_type", ""), 30000)
    return base * max(content_count, 1)


def _estimate_engagement(task_type: str) -> float:
    return {"transfer": 0.08, "match": 0.06, "news": 0.04, "trend": 0.07}.get(task_type, 0.04)


def _estimate_watch_time(content_count: int) -> int:
    return content_count * 15  # rough avg minutes per piece


def _compare_kpis(content_count: int, targets: dict[str, Any], task_type: str) -> dict[str, Any]:
    estimated_reach = _estimate_reach(content_count, {"task_type": task_type})
    target_reach = targets.get("reach", targets.get("views", 10000))
    return {
        "reach_vs_target": f"{(estimated_reach / target_reach * 100):.1f}%" if target_reach else "N/A",
        "on_track": estimated_reach >= target_reach if target_reach else True,
    }


def _generate_recommendations(plan: dict[str, Any], background: dict[str, Any]) -> list[str]:
    recs = []
    if plan.get("task_type") == "transfer":
        recs.append("Post transfer reveal video within 15 minutes of confirmation for max virality.")
    recs.append("A/B test thumbnail styles based on 30-day benchmark data.")
    recs.append("Cross-post to Telegram within 5 minutes of primary platform publish.")
    return recs
