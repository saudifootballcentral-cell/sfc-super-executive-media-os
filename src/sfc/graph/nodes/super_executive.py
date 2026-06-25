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

from sfc.ai.structured_output import extract_json
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

    # Package 7: Try AI gateway first; fall back to direct Claude call; then deterministic fallback
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    decision = None
    if api_key:
        decision = await _call_via_gateway(state)
        if decision is None:
            # Gateway failed — try direct Claude call as secondary fallback
            decision = await _call_claude(state, api_key)

    if decision is None:
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


async def _call_via_gateway(state: SFCState) -> dict[str, Any] | None:
    """Call AI gateway using ModelPolicy for executive task. Returns None on failure."""
    try:
        from sfc.ai.model_gateway import get_ai_gateway
        from sfc.ai.models import ModelRequest
        from sfc.ai.prompt_loader import get_prompt_loader

        loader = get_prompt_loader()
        system_prompt = loader.load_constitution()

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

        request = ModelRequest(
            task_type="executive",
            system_prompt=system_prompt,
            user_message=(
                f"Analyze this incoming task and return your executive decision as JSON:\n\n"
                f"{task_brief}\n\n"
                "Return ONLY a valid JSON object with EXACTLY these fields "
                "(no extra keys, no markdown, no explanation):\n"
                "{\n"
                '  "task_analysis": "<string: your analysis of this task>",\n'
                '  "priority": "<critical|high|medium|low>",\n'
                '  "risk_level": "<critical|high|medium|low>",\n'
                '  "recommended_divisions": ["intelligence", "editorial", ...],\n'
                '  "content_strategy": "<string: content approach>",\n'
                '  "routing": "planning",\n'
                '  "rationale": "<string: your reasoning>",\n'
                '  "estimated_reach": <integer>,\n'
                '  "revenue_opportunity": <true|false>\n'
                "}"
            ),
            max_tokens=1024,
            temperature=0.3,
            json_mode=True,
            output_schema="ExecutiveDecisionAI",
        )

        gateway = get_ai_gateway()
        response = await gateway.complete(request)

        if response.success and not response.used_fallback:
            if response.parsed:
                logger.info("[SuperExecutive] Gateway decision received (parsed)")
                return response.parsed
            decision = extract_json(response.text)
            if decision:
                logger.info("[SuperExecutive] Gateway decision received (text)")
                return decision

    except Exception as exc:
        logger.warning("[SuperExecutive] Gateway call failed: %s", exc)
    return None


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
        from sfc.ai.providers.claude import _sanitize_payload
        _model = "claude-opus-4-8"
        _create_kwargs: dict = {
            "model": _model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Analyze this incoming task and return your executive decision as JSON:\n\n"
                        f"{task_brief}\n\n"
                        "Return ONLY a valid JSON object with EXACTLY these fields "
                        "(no extra keys, no markdown, no explanation):\n"
                        "{\n"
                        '  "task_analysis": "<string: your analysis>",\n'
                        '  "priority": "<critical|high|medium|low>",\n'
                        '  "risk_level": "<critical|high|medium|low>",\n'
                        '  "recommended_divisions": ["intelligence", "editorial", ...],\n'
                        '  "content_strategy": "<string: content approach>",\n'
                        '  "routing": "planning",\n'
                        '  "rationale": "<string: your reasoning>",\n'
                        '  "estimated_reach": <integer>,\n'
                        '  "revenue_opportunity": <true|false>\n'
                        "}"
                    ),
                }
            ],
        }
        _sanitize_payload(_model, _create_kwargs)
        logger.info(
            "[SuperExecutive] Direct Claude request: model=%s keys=%s",
            _model, sorted(_create_kwargs.keys()),
        )
        message = await client.messages.create(**_create_kwargs)

        raw = message.content[0].text.strip()
        decision = extract_json(raw)
        if decision:
            logger.info("[SuperExecutive] Claude decision received")
            return decision
        logger.warning("[SuperExecutive] Could not parse JSON from Claude response")
        return None

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
