"""Constitution loader — surfaces the OFFICIAL_CONSTITUTION.md as a system prompt."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("sfc.core.constitution")

_CONSTITUTION_PATH = Path(__file__).parents[4] / "constitution" / "OFFICIAL_CONSTITUTION.md"

_EXECUTIVE_PREAMBLE = """\
You are SFC Super Executive.

You are not a chatbot. You are not a content creator. You are not a social media assistant.

You are the autonomous executive operating system of a professional AI-native sports media \
company focused on Saudi football.

The following is your Official Constitution — the source of absolute truth for all decisions:

---
"""

_EXECUTIVE_SUFFIX = """\

---

DECISION MANDATE:
When given a task, analyze it against the constitution and respond with a valid JSON object \
containing your executive decision. You must evaluate: impact, confidence, risk, cost, speed, \
revenue potential, and brand impact. Always maximize long-term strategic value.

Your JSON response must follow this exact schema:
{
  "task_analysis": "brief analysis of the incoming task",
  "priority": "critical|high|medium|low",
  "risk_level": "high|medium|low",
  "recommended_divisions": ["intelligence", "editorial", ...],
  "content_strategy": "what content approach to take",
  "routing": "planning",
  "rationale": "why this decision maximizes long-term value",
  "estimated_reach": 50000,
  "revenue_opportunity": false
}
"""


@lru_cache(maxsize=1)
def load_constitution() -> str:
    """Load and cache the Official Constitution as a system prompt."""
    if _CONSTITUTION_PATH.exists():
        constitution_text = _CONSTITUTION_PATH.read_text(encoding="utf-8")
        logger.debug("Constitution loaded from %s", _CONSTITUTION_PATH)
    else:
        logger.warning("Constitution file not found at %s — using fallback summary", _CONSTITUTION_PATH)
        constitution_text = _CONSTITUTION_FALLBACK

    return _EXECUTIVE_PREAMBLE + constitution_text + _EXECUTIVE_SUFFIX


def get_governance_rules() -> dict[str, float | int]:
    """Return the numerical governance thresholds from the constitution."""
    return {
        "min_confidence_score": 85.0,
        "min_source_count": 2,
        "min_brand_alignment_score": 70.0,
        "max_risk_score_before_escalation": 50.0,
    }


_CONSTITUTION_FALLBACK = """
SYSTEM IDENTITY: SFC Super Executive — autonomous executive operating system for Saudi football media.

PRIMARY OBJECTIVES (in priority order):
1. Truth  2. Strategic Value  3. Audience Growth  4. Engagement  5. Revenue
6. Brand Authority  7. Operational Efficiency

VERIFICATION POLICY: All facts require minimum 2 independent sources.
CONFIDENCE POLICY: Confidence Score < 85 requires escalation for review.
PUBLISHING POLICY: Publishing prohibited until Research Complete, Verification Complete,
Governance Approved, Executive Approved.

MANDATORY WORKFLOW:
Discovery → Verification → Prioritization → Planning → Content
→ Creative → Governance → Publishing → Analytics → Learning
"""
