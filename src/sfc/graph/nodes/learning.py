"""Learning Node — extracts lessons and updates episodic memory."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.learning")


async def learning_node(state: SFCState) -> dict[str, Any]:
    """Node: learning

    Extracts structured lessons from the completed pipeline run.
    Lessons are fed into episodic memory by memory_update_node.

    Principles from the constitution:
    - Every completed task must generate lessons learned
    - Lessons inform future executive decisions
    - Failure patterns must be recorded as clearly as successes
    """
    analytics_report = state.get("analytics_report", {})
    governance_reviews = state.get("governance_reviews", [])
    rejected_content = state.get("rejected_content", [])
    approved_content = state.get("approved_content", [])
    intelligence_report = state.get("intelligence_report", {})
    task_type = state.get("task_type", "news")
    executive_decision = state.get("executive_decision", {})

    logger.info("[Learning] Extracting lessons | run_id=%s", state["run_id"])

    lessons: list[str] = []

    # --- Governance lessons ---
    if rejected_content:
        failure_reasons = []
        for review in governance_reviews:
            if not review.get("approved"):
                failure_reasons.extend(review.get("reasons", []))
        if failure_reasons:
            lessons.append(
                f"GOVERNANCE: {len(rejected_content)} item(s) rejected. "
                f"Root causes: {'; '.join(set(failure_reasons))[:200]}"
            )

    pass_rate = len(approved_content) / max(len(governance_reviews), 1)
    if pass_rate < 0.5:
        lessons.append(
            f"QUALITY: Low governance pass rate ({pass_rate:.0%}). "
            "Source gathering must improve before editorial stage."
        )
    elif pass_rate == 1.0:
        lessons.append(
            "QUALITY: 100% governance pass rate. "
            "Intelligence → Editorial pipeline performing optimally."
        )

    # --- Intelligence lessons ---
    confidence = intelligence_report.get("confidence_score", 0.0)
    source_count = intelligence_report.get("source_count", 0)
    if source_count < 2:
        lessons.append(
            f"INTELLIGENCE: Only {source_count} source(s) found for {task_type} task. "
            "Need to expand source discovery in Package 2."
        )
    if confidence >= 90.0:
        lessons.append(
            f"INTELLIGENCE: High confidence ({confidence:.1f}%) achieved for {task_type}. "
            "Source mix and verification process working well."
        )

    # --- Analytics lessons ---
    reach = analytics_report.get("estimated_reach", 0)
    if reach > 0:
        lessons.append(
            f"ANALYTICS: Estimated reach {reach:,} for {task_type}. "
            f"Revenue signals: {analytics_report.get('revenue_signal_count', 0)}."
        )

    # --- Platform lessons ---
    recommendations = analytics_report.get("optimisation_recommendations", [])
    for rec in recommendations[:2]:
        lessons.append(f"OPTIMISATION: {rec}")

    # --- Default lesson if none extracted ---
    if not lessons:
        lessons.append(
            f"PIPELINE: {task_type} task completed successfully via full pipeline. "
            "No specific optimisations identified this run."
        )

    # Package 7: AI extracts additional patterns and recommendations
    try:
        from sfc.ai.model_gateway import get_ai_gateway
        from sfc.ai.models import ModelRequest
        import json as _json

        gateway = get_ai_gateway()
        ai_request = ModelRequest(
            task_type="learning",
            system_prompt=(
                "You are the Learning Engine for SFC Media OS. "
                "Extract patterns and lessons from pipeline runs to improve future performance."
            ),
            user_message=(
                f"Extract additional patterns and lessons from this pipeline run:\n"
                f"task_type={task_type}\n"
                f"existing_lessons={_json.dumps(lessons)}\n"
                f"approved_count={len(approved_content)}\n"
                f"rejected_count={len(rejected_content)}\n"
                f"confidence={intelligence_report.get('confidence_score', 0)}\n\n"
                "Return JSON: {\"lessons\": list[str], \"patterns\": list[str], "
                "\"recommendations\": list[str]}"
            ),
            max_tokens=512,
            json_mode=True,
            output_schema="LearningExtractionAI",
        )
        ai_response = await gateway.complete(ai_request)
        if ai_response.success and ai_response.parsed and not ai_response.used_fallback:
            parsed = ai_response.parsed
            # Extend lessons with any new AI-extracted lessons (avoid duplicates)
            for lesson in parsed.get("lessons", []):
                if lesson and lesson not in lessons:
                    lessons.append(f"AI: {lesson}")
            for rec in parsed.get("recommendations", [])[:2]:
                if rec:
                    lessons.append(f"RECOMMENDATION: {rec}")
            logger.debug("[Learning] AI extracted %d additional patterns", len(parsed.get("patterns", [])))
    except Exception as ai_exc:
        logger.debug("[Learning] AI extraction skipped: %s", ai_exc)

    logger.info("[Learning] %d lesson(s) extracted", len(lessons))

    # Persist lessons for next-cycle retrieval
    try:
        from sfc.orchestration.persistence import get_persistence_provider
        provider = get_persistence_provider()
        if hasattr(provider, "save_learning"):
            await provider.save_learning(state["run_id"], {
                "lessons": lessons,
                "task_type": task_type,
                "pass_rate": pass_rate,
                "timestamp": datetime.utcnow().isoformat(),
            })
    except Exception:
        pass  # Persistence failure never breaks the pipeline

    return {
        "lessons_learned": lessons,
        "pipeline_stage": "learning_complete",
    }
