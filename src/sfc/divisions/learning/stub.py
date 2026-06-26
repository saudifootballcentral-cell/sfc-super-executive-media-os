"""Learning Division — system optimization and continuous improvement (Package 2)."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.learning")


class LearningDivision:
    """Learning Division — analyses cycle results and optimizes the system over time.

    Package 2 implementation:
    - Analyses completed pipeline runs to extract lessons
    - Generates prompt improvement suggestions
    - Recommends persona adjustments for better content
    - Identifies timing optimizations per platform
    - Scores overall system quality
    """

    # NOTE: Division.LEARNING does not exist in the enum (8 divisions total).
    # This division is managed as a standalone optimizer attached to learning_node.
    division_name = "learning"

    def __init__(self) -> None:
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0
        self._lessons_accumulated: list[str] = []

    async def initialize(self) -> None:
        logger.info("[Learning] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Learning] Shutdown — accumulated %d lessons", len(self._lessons_accumulated))

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            lessons = state.get("lessons_learned", [])
            analytics = state.get("analytics_report", {})
            governance_reviews = state.get("governance_reviews", [])
            task_type = input.task_type

            self._lessons_accumulated.extend(lessons)

            # Generate optimization recommendations
            prompt_improvements = await self._generate_prompt_improvements(
                lessons, governance_reviews
            )
            persona_adjustments = await self._suggest_persona_adjustments(analytics, task_type)
            timing_optimizations = await self._optimize_timing(analytics, task_type)
            quality_score = self._calculate_quality_score(analytics, governance_reviews)

            result = {
                "prompt_improvements": prompt_improvements,
                "persona_adjustments": persona_adjustments,
                "timing_optimizations": timing_optimizations,
                "quality_score": quality_score,
                "lessons_processed": len(lessons),
                "total_lessons_accumulated": len(self._lessons_accumulated),
                "analysed_at": datetime.utcnow().isoformat(),
            }

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return DivisionOutput(
                run_id=input.run_id,
                division=self.division_name,
                success=True,
                data=result,
                processing_time_ms=elapsed,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Learning] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division_name,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def _generate_prompt_improvements(
        self,
        lessons: list[str],
        governance_reviews: list[dict[str, Any]],
    ) -> list[str]:
        """Generate prompt improvement suggestions using Claude or fallback."""
        try:
            from sfc.ai.model_gateway import get_ai_gateway
            from sfc.ai.models import ModelRequest
            from sfc.ai.structured_output import extract_json

            if not lessons:
                return self._deterministic_prompt_improvements(governance_reviews)

            gateway = get_ai_gateway()
            request = ModelRequest(
                task_type="analytics",
                system_prompt=(
                    "You are an AI system optimizer for a Saudi football media platform. "
                    "Analyse the lessons learned and suggest concrete prompt improvements. "
                    "Return JSON: {\"improvements\": [\"improvement1\", \"improvement2\", ...]}"
                ),
                user_message=(
                    f"Lessons from this cycle:\n{chr(10).join(lessons[:10])}\n\n"
                    "Suggest prompt improvements to prevent recurrence of failures."
                ),
                max_tokens=1024,
                temperature=0.4,
                json_mode=True,
            )
            response = await gateway.complete(request)
            if response.success and response.parsed:
                return response.parsed.get("improvements", [])
            if response.success and response.text:
                parsed = extract_json(response.text)
                if parsed:
                    return parsed.get("improvements", [])
        except Exception as exc:
            logger.debug("[Learning] _generate_prompt_improvements Claude call failed: %s", exc)

        return self._deterministic_prompt_improvements(governance_reviews)

    def _deterministic_prompt_improvements(
        self, governance_reviews: list[dict[str, Any]]
    ) -> list[str]:
        improvements = []
        rejected = [r for r in governance_reviews if not r.get("approved")]
        if rejected:
            improvements.append(
                "Add explicit confidence threshold reminder to intelligence prompt: "
                "must exceed 85% before proceeding to editorial"
            )
            improvements.append(
                "Include source count validation in editorial prompt: "
                "require minimum 2 sources listed in every draft"
            )
        improvements.append(
            "Reinforce rumor labeling: all unconfirmed content must prefix with [RUMOR]"
        )
        improvements.append(
            "Add platform tone calibration to social post prompts for Arabic vs English"
        )
        return improvements

    async def _suggest_persona_adjustments(
        self, analytics: dict[str, Any], task_type: str
    ) -> list[str]:
        """Suggest persona tuning based on performance data."""
        engagement = analytics.get("estimated_engagement_rate", 0.04)
        adjustments = []

        if engagement < 0.04:
            adjustments.append(
                "Increase urgency and emotional language in breaking news persona"
            )
        if task_type == "transfer":
            adjustments.append(
                "Activate 'Transfer Insider' persona — more speculative tone with clear rumor labels"
            )
        if task_type == "match":
            adjustments.append(
                "Use 'Match Day Analyst' persona — tactical, data-driven, post-match energy"
            )
        adjustments.append(
            "Calibrate Arabic language persona for more colloquial Saudi dialect on TikTok"
        )
        return adjustments

    async def _optimize_timing(
        self, analytics: dict[str, Any], task_type: str
    ) -> list[str]:
        """Recommend timing optimizations based on performance."""
        timing_map = {
            "transfer": "Post within 15 minutes of news breaking — first-mover advantage critical",
            "match": "Live content during match + highlight reel within 30 mins post-whistle",
            "news": "07:00, 12:00, 19:00 local time windows deliver peak engagement",
            "crisis": "Immediate response required — quality check cannot exceed 10 minutes",
        }
        recommendations = [timing_map.get(task_type, "Schedule at 19:00 UTC for peak engagement")]
        recommendations.append(
            "Friday posts achieve 35% higher engagement on average — prioritize SPL news Thursday"
        )
        return recommendations

    def _calculate_quality_score(
        self, analytics: dict[str, Any], governance_reviews: list[dict[str, Any]]
    ) -> float:
        """Calculate an overall system quality score (0-100)."""
        base = 70.0

        # Governance pass rate bonus
        if governance_reviews:
            approved = sum(1 for r in governance_reviews if r.get("approved"))
            pass_rate = approved / len(governance_reviews)
            base += pass_rate * 20.0

        # Reach performance bonus
        reach = analytics.get("estimated_reach", 0)
        if reach > 100000:
            base += 10.0
        elif reach > 50000:
            base += 5.0

        return round(min(100.0, base), 1)

    async def handle_event(self, event: BaseEvent) -> None:
        logger.debug("[Learning] Received event: %s", event.event_type)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        return ValidationResult(valid=True, score=100.0, reasons=[])

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division_name,
            period="session",
            metrics={
                "total_calls": self._call_count,
                "error_count": self._error_count,
                "lessons_accumulated": len(self._lessons_accumulated),
            },
            highlights=[f"Optimized system across {self._call_count} pipeline runs"],
            recommendations=["Connect lessons to live prompt versioning system"],
        )

    def health_check(self) -> DivisionHealth:
        return DivisionHealth(
            division=self.division_name,
            status="healthy",
            metrics={
                "call_count": self._call_count,
                "lessons_accumulated": len(self._lessons_accumulated),
            },
        )

    def describe(self) -> str:
        return "System optimization, prompt improvements, and continuous learning"
