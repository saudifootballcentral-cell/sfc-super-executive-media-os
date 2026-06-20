"""Planning Node — converts the executive decision into a detailed execution plan.

Background tasks (analytics_background, revenue_background) are executed here
using asyncio.gather() — true parallelism without LangGraph fan-in topology issues.
Their results are written to state and consumed downstream by analytics_node.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from sfc.core.models import Division, Platform
from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.planning")

# Default platforms per content type
_PLATFORM_MAP: dict[str, list[str]] = {
    "news": [Platform.X, Platform.TELEGRAM, Platform.WEBSITE, Platform.INSTAGRAM_FEED],
    "match": [Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.YOUTUBE_SHORTS, Platform.X],
    "transfer": [
        Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.X,
        Platform.YOUTUBE_SHORTS, Platform.TELEGRAM, Platform.WEBSITE,
    ],
    "trend": [Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.YOUTUBE_SHORTS],
    "crisis": [Platform.X, Platform.TELEGRAM, Platform.WEBSITE],
    "analysis": [Platform.YOUTUBE, Platform.WEBSITE, Platform.NEWSLETTER],
    "campaign": [
        Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.INSTAGRAM_FEED,
        Platform.YOUTUBE, Platform.X,
    ],
}

_CONTENT_TYPES_MAP: dict[str, list[str]] = {
    "news": ["breaking_news_article", "social_post", "telegram_update"],
    "match": ["match_report", "highlight_clip", "live_update", "social_post"],
    "transfer": ["transfer_story", "short_video", "graphic_announcement", "analysis_thread"],
    "trend": ["trend_analysis", "short_video", "carousel"],
    "crisis": ["crisis_statement", "clarification_post"],
    "analysis": ["long_form_analysis", "video_essay", "newsletter_edition"],
    "campaign": ["campaign_hero_video", "teaser_clips", "social_posts", "newsletter"],
}

_KPI_TARGETS: dict[str, dict[str, Any]] = {
    "news": {"reach": 50_000, "engagement_rate": 0.04, "share_rate": 0.02},
    "match": {"reach": 200_000, "watch_time_min": 120_000, "engagement_rate": 0.06},
    "transfer": {"reach": 500_000, "engagement_rate": 0.08, "shares": 5_000},
    "trend": {"reach": 300_000, "engagement_rate": 0.07},
    "crisis": {"reach": 100_000, "sentiment_score": 0.7},
    "analysis": {"views": 20_000, "watch_time_min": 500_000, "newsletter_open_rate": 0.35},
    "campaign": {"reach": 1_000_000, "conversion_rate": 0.01, "revenue_usd": 50_000},
}


async def planning_node(state: SFCState) -> dict[str, Any]:
    """Node: planning

    Translates the executive decision into a concrete execution plan.
    Runs analytics background analysis and revenue scanning concurrently
    via asyncio.gather() — parallel when beneficial, sequential when required.

    Returns:
        execution_plan, analytics_background_data, revenue_signals
    """
    task_type = state.get("task_type", "news")
    decision = state.get("executive_decision", {})

    logger.info("[Planning] Building execution plan for task_type=%s", task_type)

    platforms = [
        p.value if hasattr(p, "value") else p
        for p in _PLATFORM_MAP.get(task_type, [Platform.X, Platform.WEBSITE])
    ]
    content_types = _CONTENT_TYPES_MAP.get(task_type, ["article"])
    kpi_targets = _KPI_TARGETS.get(task_type, {"reach": 10_000})

    plan = {
        "plan_id": str(uuid.uuid4()),
        "task_type": task_type,
        "priority": decision.get("priority", "medium"),
        "divisions_required": decision.get("recommended_divisions", []),
        "platforms_targeted": platforms,
        "content_types": content_types,
        "kpi_targets": kpi_targets,
        "parallel_tasks": ["analytics_background", "revenue_background"],
        "sequential_tasks": ["intelligence", "editorial", "creative", "governance", "publishing"],
        "estimated_duration_minutes": _estimate_duration(task_type, decision),
        "content_strategy": decision.get("content_strategy", "Standard pipeline"),
        "revenue_opportunity": decision.get("revenue_opportunity", False),
        "created_at": datetime.utcnow().isoformat(),
    }

    # Run background tasks concurrently — write results to state here so
    # analytics_node can read them without needing a fan-in topology.
    background_state = {**state, "execution_plan": plan}
    bg_data, rev_signals = await asyncio.gather(
        _analytics_background(background_state),
        _revenue_background(background_state),
    )

    logger.info(
        "[Planning] Plan + background complete: %d platforms, %d revenue signals",
        len(platforms),
        len(rev_signals),
    )

    return {
        "execution_plan": plan,
        "analytics_background_data": bg_data,
        "revenue_signals": rev_signals,
        "pipeline_stage": "planning_complete",
    }


# ---------------------------------------------------------------------------
# Background task implementations (called concurrently from planning_node)
# ---------------------------------------------------------------------------

async def _analytics_background(state: dict[str, Any]) -> dict[str, Any]:
    """Historical benchmark analysis — runs concurrently during planning."""
    task_type = state.get("task_type", "news")
    plan = state.get("execution_plan", {})
    platforms = plan.get("platforms_targeted", [])

    benchmarks: dict[str, Any] = {}
    for platform in platforms:
        benchmarks[platform] = {
            "avg_reach_30d": {"tiktok": 80000, "instagram_reels": 45000}.get(platform, 20000),
            "avg_engagement": {"tiktok": 0.07, "instagram_reels": 0.05}.get(platform, 0.03),
        }

    patterns: dict[str, list[str]] = {
        "transfer": ["player reveal video", "wage comparison graphic", "reaction thread"],
        "match": ["highlight reel", "tactical breakdown", "player ratings"],
        "news": ["breaking header", "context thread", "reaction poll"],
    }

    return {
        "analysis_type": "historical_benchmark",
        "task_type": task_type,
        "benchmarks": benchmarks,
        "top_performing_content_patterns": patterns.get(task_type, ["standard content"]),
        "optimal_publish_times": {p: "19:00 UTC" for p in platforms},
        "audience_insights": {
            "primary_demographic": "18-34 Saudi football fans",
            "peak_engagement_day": "Friday",
            "peak_engagement_hour_utc": 19,
        },
        "analysed_at": datetime.utcnow().isoformat(),
    }


_REVENUE_OPPORTUNITIES: dict[str, list[dict[str, Any]]] = {
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


async def _revenue_background(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Sponsor and monetisation signal scan — runs concurrently during planning."""
    task_type = state.get("task_type", "news")
    plan = state.get("execution_plan", {})

    opportunities = _REVENUE_OPPORTUNITIES.get(task_type, [])
    if not opportunities:
        return []

    signals: list[dict[str, Any]] = []
    for opp in opportunities:
        signals.append({
            **opp,
            "activation_type": "sponsored_content",
            "platforms": plan.get("platforms_targeted", [])[:3],
            "detected_at": datetime.utcnow().isoformat(),
            "status": "opportunity",
        })

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

    return signals


def _estimate_duration(task_type: str, decision: dict[str, Any]) -> int:
    base = {
        "news": 15, "match": 30, "transfer": 20, "trend": 25,
        "crisis": 10, "analysis": 60, "campaign": 120,
    }
    priority_multiplier = {"critical": 0.5, "high": 0.75, "medium": 1.0, "low": 1.5}
    priority = decision.get("priority", "medium")
    return int(base.get(task_type, 30) * priority_multiplier.get(priority, 1.0))
