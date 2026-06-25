"""Pydantic models for validated AI outputs + JSON extraction utilities."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("sfc.ai.structured_output")


# ---------------------------------------------------------------------------
# Pydantic models for validated AI outputs
# ---------------------------------------------------------------------------

class ExecutiveDecisionAI(BaseModel):
    """Executive decision returned by the super-executive node.

    All fields have defaults so that partial Claude responses still validate
    (7-field validation failures caused by field-name mismatches are recovered
    by the explicit JSON template in the prompt; these defaults are the safety net).
    """
    task_analysis: str = ""
    priority: str = "medium"       # critical|high|medium|low
    risk_level: str = "medium"     # critical|high|medium|low
    recommended_divisions: list[str] = Field(
        default_factory=lambda: ["intelligence", "editorial", "creative", "governance", "publishing"]
    )
    content_strategy: str = ""
    routing: str = "planning"      # "planning" or "abort"
    rationale: str = ""
    estimated_reach: int = 0
    revenue_opportunity: bool = False


class IntelligenceReportAI(BaseModel):
    summary: str
    key_facts: list[str]
    confidence_score: float  # 0-100
    is_rumor: bool = False
    rumor_label: str | None = None
    sources_used: list[str] = Field(default_factory=list)
    opportunity_detected: bool = False


class ContentDraftAI(BaseModel):
    title: str
    body: str
    content_type: str
    key_messages: list[str]
    tone: str = "professional"
    cta: str = ""


class CreativeBriefAI(BaseModel):
    concept: str
    visual_direction: str
    key_elements: list[str]
    color_palette: list[str] = Field(default_factory=list)
    format_specs: dict[str, str] = Field(default_factory=dict)


class LearningExtractionAI(BaseModel):
    lessons: list[str]
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# Registry of schema classes by name
_SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "ExecutiveDecisionAI": ExecutiveDecisionAI,
    "IntelligenceReportAI": IntelligenceReportAI,
    "ContentDraftAI": ContentDraftAI,
    "CreativeBriefAI": CreativeBriefAI,
    "LearningExtractionAI": LearningExtractionAI,
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def repair_json(text: str) -> str | None:
    """Attempt heuristic repair of common LLM JSON issues.

    Handles: trailing commas, unterminated strings, unclosed braces/brackets.
    Returns the repaired JSON string, or None if unrepairable.
    """
    s = text.strip()
    if not s:
        return None

    # Remove trailing commas: before } or ], and at end of string (truncated response)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    s = re.sub(r",\s*$", "", s)
    s = re.sub(r",\s*([}\]])", r"\1", s)  # second pass for nested cases

    # Walk to find structural state (respects escapes and quoted strings)
    in_str = False
    escape_next = False
    depth_brace = 0
    depth_bracket = 0
    last_complete_pos = 0

    for idx, ch in enumerate(s):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_str:
            escape_next = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
            if depth_brace == 0 and depth_bracket == 0:
                last_complete_pos = idx + 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1
            if depth_brace == 0 and depth_bracket == 0:
                last_complete_pos = idx + 1

    # Already valid
    if not in_str and depth_brace == 0 and depth_bracket == 0:
        try:
            json.loads(s)
            return s
        except json.JSONDecodeError:
            pass

    # Close unterminated string then open structures
    suffix = ('"' if in_str else "") + "]" * max(0, depth_bracket) + "}" * max(0, depth_brace)
    repaired = s + suffix
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        pass

    # Last resort: truncate to last known balanced position
    if last_complete_pos > 0:
        truncated = s[:last_complete_pos]
        try:
            json.loads(truncated)
            return truncated
        except json.JSONDecodeError:
            pass

    return None


def _strip_fences(text: str) -> list[str]:
    """Return candidate strings with markdown fences stripped (multiple strategies)."""
    candidates: list[str] = []

    # Strategy 1: complete ```json ... ``` or ``` ... ``` fences
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    for m in fence_pattern.finditer(text):
        candidates.append(m.group(1).strip())

    # Strategy 2: unclosed fence — content after the opening ```
    unclosed = re.search(r"```(?:json)?\s*([\s\S]+)$", text, re.IGNORECASE)
    if unclosed:
        candidates.append(unclosed.group(1).strip())

    return candidates


def extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from AI response, with repair for common LLM syntax errors."""
    if not text:
        return {}

    text_stripped = text.strip()

    # 1. Try fence-stripped candidates first
    for candidate in _strip_fences(text_stripped):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = repair_json(candidate)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    # 2. Try raw text
    try:
        return json.loads(text_stripped)
    except json.JSONDecodeError:
        pass

    # 3. Find the outermost {...} block
    brace_match = re.search(r"\{[\s\S]*\}", text_stripped)
    if brace_match:
        block = brace_match.group(0)
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            repaired = repair_json(block)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    # 4. Attempt repair on the full stripped text
    repaired = repair_json(text_stripped)
    if repaired:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    logger.warning("[StructuredOutput] Could not extract JSON from response")
    return {}


def validate_output(
    text: str,
    schema: type[BaseModel],
) -> tuple[BaseModel | None, str | None]:
    """Parse and validate AI output.

    Returns:
        (model_instance, None) on success
        (None, error_message) on failure
    """
    data = extract_json(text)
    if not data:
        return None, f"Could not extract JSON from AI response (text length={len(text)})"

    try:
        instance = schema(**data)
        return instance, None
    except Exception as exc:
        return None, f"Validation failed for {schema.__name__}: {exc}"


def get_schema_class(name: str) -> type[BaseModel] | None:
    """Return the Pydantic schema class by name, or None if not found."""
    return _SCHEMA_REGISTRY.get(name)
