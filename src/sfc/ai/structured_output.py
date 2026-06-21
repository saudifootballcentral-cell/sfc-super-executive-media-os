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
    task_analysis: str
    priority: str  # critical|high|medium|low
    risk_level: str  # critical|high|medium|low
    recommended_divisions: list[str]
    content_strategy: str
    routing: str  # "planning" or "abort"
    rationale: str
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

def extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from AI response, stripping markdown fences."""
    if not text:
        return {}

    # Try to strip markdown code fences
    # Match ```json ... ``` or ``` ... ```
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    match = fence_pattern.search(text)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try the raw text
    text_stripped = text.strip()
    try:
        return json.loads(text_stripped)
    except json.JSONDecodeError:
        pass

    # Try to find the first {...} block
    brace_match = re.search(r"\{[\s\S]*\}", text_stripped)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
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
