"""Manages deterministic fallbacks when all AI providers fail."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.ai.models import ModelRequest, ModelResponse

logger = logging.getLogger("sfc.ai.fallback_manager")


class FallbackManager:
    """Returns deterministic fallback data when AI providers fail."""

    def get_fallback(self, request: ModelRequest) -> ModelResponse:
        """Return a deterministic fallback response for this task_type."""
        task_type = request.task_type
        logger.info("[FallbackManager] Providing deterministic fallback for task_type=%s", task_type)

        text = self._get_fallback_text(task_type, request)
        return ModelResponse(
            success=True,
            text=text,
            parsed=self._get_fallback_parsed(task_type, request),
            provider="fallback",
            model="deterministic",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=0,
            used_fallback=True,
            validation_failed=False,
            error="",
        )

    def _get_fallback_text(self, task_type: str, request: ModelRequest) -> str:
        context = request.context
        task = context.get("task_type", "news")

        if task_type == "executive":
            return (
                f'{{"task_analysis": "Detected {task} task requiring full pipeline execution.", '
                f'"priority": "high", "risk_level": "medium", '
                f'"recommended_divisions": ["intelligence", "editorial", "creative", "governance", "publishing", "analytics"], '
                f'"content_strategy": "Standard multi-platform content production.", '
                f'"routing": "planning", '
                f'"rationale": "Fallback decision — all divisions engaged for maximum coverage.", '
                f'"estimated_reach": 50000, "revenue_opportunity": false}}'
            )

        if task_type == "editorial":
            headline = context.get("headline", "Saudi Football Update")
            return (
                f'{{"title": "{headline}", '
                f'"body": "Comprehensive coverage of the latest Saudi football developments.", '
                f'"content_type": "article", '
                f'"key_messages": ["Key development in Saudi football", "Full analysis available"], '
                f'"tone": "professional", "cta": "Read more on our platform"}}'
            )

        if task_type == "intelligence":
            return (
                '{"summary": "Intelligence analysis complete via deterministic fallback.", '
                '"key_facts": ["Saudi football continues to develop", "Key stakeholders engaged"], '
                '"confidence_score": 70.0, "is_rumor": false, "rumor_label": null, '
                '"sources_used": [], "opportunity_detected": false}'
            )

        if task_type == "governance":
            return (
                '{"explanation": "Constitutional compliance check completed via code-based rules.", '
                '"suggestions": ["Ensure minimum 2 verified sources", "Maintain confidence score above 85"], '
                '"code_check_is_authoritative": true}'
            )

        if task_type == "creative":
            return (
                '{"concept": "Dynamic Saudi football content with strong visual identity.", '
                '"visual_direction": "Bold, modern aesthetic reflecting Saudi football culture.", '
                '"key_elements": ["Team colors", "Action shots", "Score overlay"], '
                '"color_palette": ["#006C35", "#FFFFFF", "#000000"], '
                '"format_specs": {"aspect_ratio": "16:9", "format": "mp4"}}'
            )

        if task_type in ("persona", "strategic_planning"):
            return (
                '{"insights": "Persona analysis complete. Standard content strategy recommended.", '
                '"recommendations": ["Target core fan demographics", "Optimize for peak engagement hours"]}'
            )

        if task_type == "revenue":
            return (
                '{"revenue_insights": "Revenue signals processed.", '
                '"top_opportunities": [], '
                '"total_estimated_value_usd": 0, '
                '"priority_actions": ["Monitor sponsorship opportunities"]}'
            )

        if task_type == "learning":
            return (
                '{"lessons": ["Pipeline completed successfully via fallback path."], '
                '"patterns": ["Fallback execution maintains system stability"], '
                '"recommendations": ["Configure AI API keys for enhanced analysis"]}'
            )

        # Default fallback for any other task_type
        return (
            '{"result": "Deterministic fallback response.", '
            '"task_type": "' + task_type + '", '
            '"status": "fallback_used"}'
        )

    def _get_fallback_parsed(self, task_type: str, request: ModelRequest) -> dict[str, Any]:
        """Return parsed dict version matching the fallback text."""
        context = request.context
        task = context.get("task_type", "news")

        if task_type == "executive":
            return {
                "task_analysis": f"Detected {task} task requiring full pipeline execution.",
                "priority": "high",
                "risk_level": "medium",
                "recommended_divisions": [
                    "intelligence", "editorial", "creative",
                    "governance", "publishing", "analytics",
                ],
                "content_strategy": "Standard multi-platform content production.",
                "routing": "planning",
                "rationale": "Fallback decision — all divisions engaged for maximum coverage.",
                "estimated_reach": 50000,
                "revenue_opportunity": False,
            }

        if task_type == "editorial":
            headline = context.get("headline", "Saudi Football Update")
            return {
                "title": headline,
                "body": "Comprehensive coverage of the latest Saudi football developments.",
                "content_type": "article",
                "key_messages": ["Key development in Saudi football", "Full analysis available"],
                "tone": "professional",
                "cta": "Read more on our platform",
            }

        if task_type == "intelligence":
            return {
                "summary": "Intelligence analysis complete via deterministic fallback.",
                "key_facts": ["Saudi football continues to develop", "Key stakeholders engaged"],
                "confidence_score": 70.0,
                "is_rumor": False,
                "rumor_label": None,
                "sources_used": [],
                "opportunity_detected": False,
            }

        if task_type == "governance":
            return {
                "explanation": "Constitutional compliance check completed via code-based rules.",
                "suggestions": [
                    "Ensure minimum 2 verified sources",
                    "Maintain confidence score above 85",
                ],
                "code_check_is_authoritative": True,
            }

        if task_type == "creative":
            return {
                "concept": "Dynamic Saudi football content with strong visual identity.",
                "visual_direction": "Bold, modern aesthetic reflecting Saudi football culture.",
                "key_elements": ["Team colors", "Action shots", "Score overlay"],
                "color_palette": ["#006C35", "#FFFFFF", "#000000"],
                "format_specs": {"aspect_ratio": "16:9", "format": "mp4"},
            }

        if task_type in ("persona", "strategic_planning"):
            return {
                "insights": "Persona analysis complete. Standard content strategy recommended.",
                "recommendations": [
                    "Target core fan demographics",
                    "Optimize for peak engagement hours",
                ],
            }

        if task_type == "revenue":
            return {
                "revenue_insights": "Revenue signals processed.",
                "top_opportunities": [],
                "total_estimated_value_usd": 0,
                "priority_actions": ["Monitor sponsorship opportunities"],
            }

        if task_type == "learning":
            return {
                "lessons": ["Pipeline completed successfully via fallback path."],
                "patterns": ["Fallback execution maintains system stability"],
                "recommendations": ["Configure AI API keys for enhanced analysis"],
            }

        return {
            "result": "Deterministic fallback response.",
            "task_type": task_type,
            "status": "fallback_used",
        }
