"""Super Executive Node — Claude is the executive decision-maker.

This is the only node that calls an LLM directly. Claude receives the full
Official Constitution as its system prompt, analyzes the incoming task, and
returns a structured JSON executive decision that routes the rest of the pipeline.

Model: claude-opus-4-8 (most capable — executive decisions require highest intelligence)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from sfc.core.constitution import load_constitution
from sfc.core.models import Division, ExecutiveDecision, Priority, RiskLevel
from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.super_executive")

_DEFAULT_PRIORITY_MAP = {
    "match": Priority.HIGH,
    "transfer": Priority.HIGH,
    "crisis": Priority.CRITICAL,
    "news": Priority.MEDIUM,
    "trend": Priority.MEDIUM,
    "analysis": Priority.LOW,
    "campaign": Priority.MEDIUM,
}


async def super_executive_node(state: SFCState) -> dict[str, Any]:
    """Node: super_executive

    Claude (claude-opus-4-8) reads the Official Constitution and makes the
    executive decision: priority, risk, which divisions to involve, content
    strategy, and routing.
    """
    logger.info("[SuperExecutive] Analyzing task: %s | run_id=%s", state["task_type"], state["run_id"])

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if api_key:
        decision = await _call_claude(state, api_key)
    else:
        logger.warning("[SuperExecutive] No ANTHROPIC_API_KEY — using deterministic fallback decision")
        decision = _fallback_decision(state)

    logger.info(
        "[SuperExecutive] Decision: priority=%s risk=%s routing=%s",
        decision.get("priority"),
        decision.get("risk_level"),
        decision.get("routing"),
    )

    return {
        "executive_decision": decision,
        "pipeline_stage": "executive_complete",
    }


async def _call_claude(state: SFCState, api_key: str) -> dict[str, Any]:
    """Call Claude with the constitution as system prompt to get the executive decision."""
    try:
        import anthropic
    except ImportError:
        logger.error("[SuperExecutive] anthropic package not installed — using fallback")
        return _fallback_decision(state)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    system_prompt = load_constitution()

    task_brief = json.dumps(
        {
            "task_type": state["task_type"],
            "payload": state["task_payload"],
            "run_id": state["run_id"],
            "timestamp": state["started_at"],
        },
        ensure_ascii=False,
        indent=2,
    )

    try:
        message = await client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze this incoming task and return your executive decision as JSON:\n\n"
                        f"{task_brief}\n\n"
                        "Return ONLY valid JSON matching the schema in your instructions."
                    ),
                }
            ],
        )

        raw = message.content[0].text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        decision = json.loads(raw)
        logger.info("[SuperExecutive] Claude decision received")
        return decision

    except Exception as exc:
        logger.error("[SuperExecutive] Claude call failed: %s — falling back", exc)
        fallback = _fallback_decision(state)
        fallback["_fallback_reason"] = str(exc)
        return fallback


def _fallback_decision(state: SFCState) -> dict[str, Any]:
    """Deterministic executive decision used when Claude is unavailable."""
    task_type = state.get("task_type", "news")
    priority = _DEFAULT_PRIORITY_MAP.get(task_type, Priority.MEDIUM)

    all_divisions = [
        Division.INTELLIGENCE,
        Division.EDITORIAL,
        Division.CREATIVE,
        Division.GOVERNANCE,
        Division.PUBLISHING,
        Division.ANALYTICS,
        Division.REVENUE,
    ]

    return {
        "task_analysis": f"Detected {task_type} task requiring full pipeline execution.",
        "priority": priority.value if hasattr(priority, "value") else priority,
        "risk_level": RiskLevel.MEDIUM.value,
        "recommended_divisions": [d.value for d in all_divisions],
        "content_strategy": "Standard multi-platform content production.",
        "routing": "planning",
        "rationale": "Fallback decision — all divisions engaged for maximum coverage.",
        "estimated_reach": 50_000,
        "revenue_opportunity": task_type in ("transfer", "match", "campaign"),
    }
