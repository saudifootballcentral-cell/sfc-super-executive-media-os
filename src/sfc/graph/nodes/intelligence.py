"""Intelligence Node — discovery, monitoring, and fact verification.

Runs in PARALLEL with analytics_background and revenue_background.
This is the primary parallel node: its output feeds the editorial node.

Package 2: IntelligenceDivision will replace the stub logic below.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.intelligence")

# Minimum sources required by the Official Constitution
MIN_SOURCES = 2


async def intelligence_node(state: SFCState) -> dict[str, Any]:
    """Node: intelligence  [PARALLEL PHASE — primary]

    Responsibilities:
    - Trend detection
    - News monitoring
    - Rumor tracking and labeling
    - Source verification (min 2 sources required)
    - Opportunity identification

    Returns: intelligence_report, verified_sources
    """
    task_type = state.get("task_type", "news")
    payload = state.get("task_payload", {})
    plan = state.get("execution_plan", {})

    logger.info("[Intelligence] Starting research | task=%s", task_type)

    try:
        # Package 2: Call IntelligenceService with fallback to stub logic
        try:
            from sfc.divisions.intelligence.service import IntelligenceService
            from sfc.divisions.base import DivisionInput
            service = IntelligenceService()
            await service.initialize()
            result = await service.execute(DivisionInput(
                run_id=state.get("run_id", ""),
                task_type=task_type,
                payload=payload,
                state_snapshot=dict(state),
            ))
            if result.success and result.data:
                report_out = result.data.get("intelligence_report", {})
                sources_out = result.data.get("verified_sources", [])
                return {
                    "intelligence_report": report_out,
                    "verified_sources": sources_out,
                    "pipeline_stage": "intelligence_complete",
                }
        except Exception as svc_exc:
            logger.warning("[Intelligence] Service call failed, using stub: %s", svc_exc)

        verified_sources = _gather_sources(payload)
        source_count = len(verified_sources)

        if source_count < MIN_SOURCES:
            logger.warning(
                "[Intelligence] Only %d source(s) found — minimum %d required. "
                "Content will fail governance.",
                source_count,
                MIN_SOURCES,
            )

        is_rumor = payload.get("is_rumor", False)
        confidence = _calculate_confidence(source_count, payload)

        report: dict[str, Any] = {
            "task_type": task_type,
            "research_complete": True,
            "is_rumor": is_rumor,
            "rumor_label": "RUMOR — unconfirmed" if is_rumor else None,
            "confidence_score": confidence,
            "source_count": source_count,
            "key_facts": _extract_key_facts(payload),
            "entities_detected": _detect_entities(payload),
            "sentiment": "neutral",
            "newsworthiness_score": _score_newsworthiness(task_type, payload),
            "researched_at": datetime.utcnow().isoformat(),
        }

        # Package 7: Optionally enhance key_facts via AI gateway
        # CRITICAL: verified_sources count NEVER inflated by AI
        try:
            from sfc.ai.model_gateway import get_ai_gateway
            from sfc.ai.models import ModelRequest
            from sfc.ai.prompt_loader import get_prompt_loader

            loader = get_prompt_loader()
            system_prompt = loader.load("divisions", "intelligence")
            gateway = get_ai_gateway()
            ai_request = ModelRequest(
                task_type="intelligence",
                system_prompt=system_prompt,
                user_message=(
                    f"Analyze this intelligence data and provide enhanced key facts and summary:\n"
                    f"task_type={task_type}\n"
                    f"key_facts={report['key_facts']}\n"
                    f"confidence={confidence}\n"
                    f"source_count={source_count} (DO NOT change this count)\n"
                    f"is_rumor={is_rumor}\n\n"
                    "Return JSON: {\"summary\": str, \"key_facts\": list[str], "
                    "\"confidence_score\": float (use same as input), "
                    "\"opportunity_detected\": bool}"
                ),
                max_tokens=512,
                json_mode=True,
                output_schema="IntelligenceReportAI",
            )
            ai_response = await gateway.complete(ai_request)
            if ai_response.success and ai_response.parsed and not ai_response.used_fallback:
                parsed = ai_response.parsed
                # Only enrich key_facts and add summary — never modify source counts
                if parsed.get("key_facts"):
                    report["key_facts"] = parsed["key_facts"]
                if parsed.get("summary"):
                    report["ai_summary"] = parsed["summary"]
                if parsed.get("opportunity_detected"):
                    report["opportunity_detected"] = parsed["opportunity_detected"]
                # CRITICAL: confidence_score and source_count are NEVER taken from AI
                logger.debug("[Intelligence] AI enrichment applied (key_facts updated)")
        except Exception as ai_exc:
            logger.debug("[Intelligence] AI enhancement skipped: %s", ai_exc)

        logger.info(
            "[Intelligence] Research complete | sources=%d confidence=%.1f%%",
            source_count,
            confidence,
        )

        return {
            "intelligence_report": report,
            "verified_sources": verified_sources,
            "pipeline_stage": "intelligence_complete",
        }

    except Exception as exc:
        logger.error("[Intelligence] Failed: %s", exc, exc_info=True)
        return {
            "intelligence_report": {"research_complete": False, "error": str(exc)},
            "verified_sources": [],
            "errors": [f"INTELLIGENCE: {exc}"],
        }


def _gather_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and normalise sources from the payload."""
    raw_sources = payload.get("sources", [])
    normalised = []
    for s in raw_sources:
        if isinstance(s, dict):
            normalised.append({
                "name": s.get("name", "Unknown"),
                "url": s.get("url"),
                "reliability_score": float(s.get("reliability", s.get("reliability_score", 80.0))),
                "retrieved_at": datetime.utcnow().isoformat(),
            })
    return normalised


def _calculate_confidence(source_count: int, payload: dict[str, Any]) -> float:
    """Calculate confidence score based on sources and payload metadata."""
    base = 60.0
    source_bonus = min(source_count * 12.0, 30.0)
    payload_bonus = 5.0 if payload.get("official_statement") else 0.0
    is_rumor_penalty = -10.0 if payload.get("is_rumor") else 0.0
    return min(100.0, base + source_bonus + payload_bonus + is_rumor_penalty)


def _extract_key_facts(payload: dict[str, Any]) -> list[str]:
    facts = []
    if payload.get("headline"):
        facts.append(payload["headline"])
    if payload.get("key_facts"):
        facts.extend(payload["key_facts"])
    if not facts:
        facts.append(payload.get("body", "")[:200] if payload.get("body") else "No facts extracted")
    return facts


def _detect_entities(payload: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "players": payload.get("players", []),
        "clubs": payload.get("clubs", []),
        "competitions": payload.get("competitions", ["Saudi Pro League"]),
        "coaches": payload.get("coaches", []),
    }


def _score_newsworthiness(task_type: str, payload: dict[str, Any]) -> float:
    base_scores = {
        "crisis": 95.0, "transfer": 85.0, "match": 80.0,
        "news": 70.0, "trend": 65.0, "analysis": 60.0, "campaign": 55.0,
    }
    score = base_scores.get(task_type, 60.0)
    if payload.get("importance_score"):
        score = (score + float(payload["importance_score"])) / 2
    return round(score, 1)
