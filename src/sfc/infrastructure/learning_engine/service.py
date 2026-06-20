"""Learning Engine — continuous improvement from every workflow outcome."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus

if TYPE_CHECKING:
    from sfc.infrastructure.memory_manager.service import MemoryManagerService

logger = logging.getLogger("sfc.infrastructure.learning_engine")


class LessonType(str, Enum):
    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"
    OPTIMIZATION = "optimization"
    EMERGING_TREND = "emerging_trend"
    WORKFLOW_IMPROVEMENT = "workflow_improvement"


class Lesson(BaseModel):
    """A single learning lesson extracted from workflow outcomes."""

    lesson_id: UUID = Field(default_factory=uuid4)
    lesson_type: LessonType
    division: str
    run_id: str
    observation: str
    recommendation: str
    confidence: float  # 0-100
    impact: str  # "high", "medium", "low"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    applied: bool = False
    tags: list[str] = Field(default_factory=list)


class LearningEngineService:
    """Continuous improvement engine.

    Learning triggers:
    - Every completed workflow
    - Every governance rejection
    - Content performing >2x benchmark
    - Same failure pattern ≥3 times
    """

    def __init__(self, memory_manager: MemoryManagerService | None = None) -> None:
        self._lessons: list[Lesson] = []
        self._memory = memory_manager
        self._failure_pattern_counts: dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Analysis Methods
    # ------------------------------------------------------------------

    async def analyze_workflow(self, state_snapshot: dict[str, Any]) -> list[Lesson]:
        """Extract lessons from a completed workflow run."""
        lessons: list[Lesson] = []
        run_id = state_snapshot.get("run_id", "unknown")
        task_type = state_snapshot.get("task_type", "unknown")

        approved = state_snapshot.get("approved_content", [])
        rejected = state_snapshot.get("rejected_content", [])
        analytics = state_snapshot.get("analytics_report", {})
        pipeline_stage = state_snapshot.get("pipeline_stage", "")

        # Lesson: approval rate
        total = len(approved) + len(rejected)
        if total > 0:
            approval_rate = len(approved) / total
            if approval_rate >= 0.9:
                lesson = Lesson(
                    lesson_type=LessonType.SUCCESS_PATTERN,
                    division="governance",
                    run_id=run_id,
                    observation=f"High approval rate {approval_rate:.0%} for {task_type} content",
                    recommendation=f"Replicate {task_type} content strategy in future campaigns",
                    confidence=80.0,
                    impact="high",
                    tags=[task_type, "governance", "approval"],
                )
                lessons.append(lesson)
            elif approval_rate < 0.5:
                self._failure_pattern_counts[f"low_approval_{task_type}"] += 1
                lesson = Lesson(
                    lesson_type=LessonType.FAILURE_PATTERN,
                    division="governance",
                    run_id=run_id,
                    observation=f"Low approval rate {approval_rate:.0%} for {task_type} content",
                    recommendation="Review editorial brief quality and source verification process",
                    confidence=85.0,
                    impact="high",
                    tags=[task_type, "governance", "rejection"],
                )
                lessons.append(lesson)

        # Lesson: reach performance
        estimated_reach = analytics.get("estimated_reach", 0)
        if estimated_reach > 1_000_000:
            lesson = Lesson(
                lesson_type=LessonType.SUCCESS_PATTERN,
                division="analytics",
                run_id=run_id,
                observation=f"Outstanding reach of {estimated_reach:,} for {task_type}",
                recommendation="Document content formula for replication in future runs",
                confidence=90.0,
                impact="high",
                tags=[task_type, "reach", "performance"],
            )
            lessons.append(lesson)

        # Lesson: pipeline completion
        errors = state_snapshot.get("errors", [])
        if errors:
            for error in errors[:3]:
                error_key = error[:50] if isinstance(error, str) else str(error)[:50]
                self._failure_pattern_counts[f"pipeline_error:{error_key}"] += 1
                lesson = Lesson(
                    lesson_type=LessonType.WORKFLOW_IMPROVEMENT,
                    division="infrastructure",
                    run_id=run_id,
                    observation=f"Pipeline error encountered: {error_key}",
                    recommendation="Investigate and add error handling or validation step",
                    confidence=70.0,
                    impact="medium",
                    tags=["error", "pipeline", task_type],
                )
                lessons.append(lesson)

        # Lesson: check for repeated failure patterns
        for pattern, count in self._failure_pattern_counts.items():
            if count >= 3:
                lesson = Lesson(
                    lesson_type=LessonType.OPTIMIZATION,
                    division="infrastructure",
                    run_id=run_id,
                    observation=f"Repeated failure pattern detected ({count}x): {pattern}",
                    recommendation=f"Generate prompt update for affected division. Pattern: {pattern}",
                    confidence=92.0,
                    impact="high",
                    tags=["repeated_failure", "prompt_update"],
                )
                lessons.append(lesson)

        with self._lock:
            self._lessons.extend(lessons)

        # Persist to memory if available
        if self._memory:
            for lesson in lessons:
                await self._memory.store("lessons", lesson.lesson_id.hex, lesson.model_dump())

        logger.info("[LearningEngine] Extracted %d lessons for run %s", len(lessons), run_id)
        return lessons

    async def analyze_governance_outcome(
        self,
        approved: list[Any],
        rejected: list[Any],
        run_id: str,
    ) -> list[Lesson]:
        """Learn from governance decisions."""
        lessons: list[Lesson] = []

        total = len(approved) + len(rejected)
        if total == 0:
            return lessons

        rejection_rate = len(rejected) / total

        if rejection_rate > 0.3:
            self._failure_pattern_counts[f"high_rejection_rate:{run_id[:8]}"] += 1
            lesson = Lesson(
                lesson_type=LessonType.FAILURE_PATTERN,
                division="governance",
                run_id=run_id,
                observation=f"High governance rejection rate: {rejection_rate:.0%} ({len(rejected)}/{total})",
                recommendation=(
                    "Review source quality requirements and editorial brief templates. "
                    "Consider adding pre-governance checklist."
                ),
                confidence=88.0,
                impact="high",
                tags=["governance", "rejection", "quality"],
            )
            lessons.append(lesson)
        elif rejection_rate == 0 and total >= 3:
            lesson = Lesson(
                lesson_type=LessonType.SUCCESS_PATTERN,
                division="governance",
                run_id=run_id,
                observation=f"Perfect governance pass rate: {total} items approved",
                recommendation="Document and replicate this content quality benchmark",
                confidence=85.0,
                impact="medium",
                tags=["governance", "approval", "quality"],
            )
            lessons.append(lesson)

        with self._lock:
            self._lessons.extend(lessons)

        return lessons

    async def analyze_content_performance(
        self,
        analytics_report: dict[str, Any],
        run_id: str,
    ) -> list[Lesson]:
        """Learn from content performance data."""
        lessons: list[Lesson] = []

        estimated_reach = analytics_report.get("estimated_reach", 0)
        benchmark_reach = analytics_report.get("benchmark_reach", 100_000)
        engagement_rate = analytics_report.get("engagement_rate", 0.0)
        revenue = analytics_report.get("total_revenue_usd", 0.0)

        # Check for viral performance (>2x benchmark)
        if benchmark_reach > 0 and estimated_reach > benchmark_reach * 2:
            lesson = Lesson(
                lesson_type=LessonType.SUCCESS_PATTERN,
                division="analytics",
                run_id=run_id,
                observation=(
                    f"Content exceeded benchmark by {estimated_reach / benchmark_reach:.1f}x: "
                    f"reach {estimated_reach:,} vs benchmark {benchmark_reach:,}"
                ),
                recommendation=(
                    "Analyze content attributes that drove viral growth — "
                    "replicate timing, format, and topic strategy."
                ),
                confidence=90.0,
                impact="high",
                tags=["viral", "performance", "benchmark"],
            )
            lessons.append(lesson)

        # Below benchmark
        if benchmark_reach > 0 and estimated_reach < benchmark_reach * 0.5:
            lesson = Lesson(
                lesson_type=LessonType.OPTIMIZATION,
                division="analytics",
                run_id=run_id,
                observation=(
                    f"Content underperformed benchmark: {estimated_reach:,} vs {benchmark_reach:,}"
                ),
                recommendation=(
                    "Review platform selection, publish timing, and content hooks. "
                    "Consider A/B testing alternative formats."
                ),
                confidence=80.0,
                impact="medium",
                tags=["underperformance", "optimization"],
            )
            lessons.append(lesson)

        # Engagement rate lesson
        if engagement_rate > 0.15:
            lesson = Lesson(
                lesson_type=LessonType.SUCCESS_PATTERN,
                division="analytics",
                run_id=run_id,
                observation=f"Exceptional engagement rate: {engagement_rate:.1%}",
                recommendation="Analyze content hooks and call-to-actions for best practices",
                confidence=85.0,
                impact="medium",
                tags=["engagement", "performance"],
            )
            lessons.append(lesson)

        # Revenue lesson
        if revenue > 500:
            lesson = Lesson(
                lesson_type=LessonType.SUCCESS_PATTERN,
                division="revenue",
                run_id=run_id,
                observation=f"Strong revenue performance: ${revenue:,.2f}",
                recommendation="Expand sponsor integration strategy for similar content types",
                confidence=80.0,
                impact="high",
                tags=["revenue", "sponsorship"],
            )
            lessons.append(lesson)

        with self._lock:
            self._lessons.extend(lessons)

        return lessons

    async def analyze_intelligence_quality(
        self,
        intelligence_report: dict[str, Any],
        run_id: str,
    ) -> list[Lesson]:
        """Learn from source quality and confidence scores."""
        lessons: list[Lesson] = []

        confidence_score = intelligence_report.get("confidence_score", 85.0)
        source_count = intelligence_report.get("source_count", 2)
        verified = intelligence_report.get("verified", True)

        if confidence_score < 60:
            lesson = Lesson(
                lesson_type=LessonType.FAILURE_PATTERN,
                division="intelligence",
                run_id=run_id,
                observation=f"Low confidence score in intelligence report: {confidence_score:.1f}/100",
                recommendation=(
                    "Expand source network and implement additional cross-verification steps. "
                    "Consider delaying publication until confidence exceeds 85."
                ),
                confidence=88.0,
                impact="high",
                tags=["intelligence", "confidence", "sources"],
            )
            lessons.append(lesson)
        elif confidence_score >= 95:
            lesson = Lesson(
                lesson_type=LessonType.SUCCESS_PATTERN,
                division="intelligence",
                run_id=run_id,
                observation=f"High confidence intelligence report: {confidence_score:.1f}/100",
                recommendation="Document successful source combination for reuse",
                confidence=85.0,
                impact="medium",
                tags=["intelligence", "confidence", "quality"],
            )
            lessons.append(lesson)

        if source_count < 2:
            lesson = Lesson(
                lesson_type=LessonType.OPTIMIZATION,
                division="intelligence",
                run_id=run_id,
                observation=f"Insufficient source count: {source_count} (minimum 2 required)",
                recommendation="Enforce minimum 2-source verification before passing to editorial",
                confidence=95.0,
                impact="high",
                tags=["intelligence", "sources", "verification"],
            )
            lessons.append(lesson)

        with self._lock:
            self._lessons.extend(lessons)

        return lessons

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_lessons(
        self,
        division: str | None = None,
        lesson_type: LessonType | None = None,
        limit: int = 20,
    ) -> list[Lesson]:
        """Query stored lessons."""
        with self._lock:
            results = list(self._lessons)

        if division:
            results = [l for l in results if l.division == division]
        if lesson_type:
            results = [l for l in results if l.lesson_type == lesson_type]

        # Return most recent first
        results = sorted(results, key=lambda l: l.created_at, reverse=True)
        return results[:limit]

    def get_best_practices(self) -> list[str]:
        """Return top success patterns as actionable strings."""
        with self._lock:
            success_lessons = [
                l for l in self._lessons
                if l.lesson_type == LessonType.SUCCESS_PATTERN
            ]

        # Sort by confidence
        success_lessons = sorted(success_lessons, key=lambda l: l.confidence, reverse=True)

        return [
            f"[{l.impact.upper()}] {l.recommendation} (confidence: {l.confidence:.0f}%)"
            for l in success_lessons[:10]
        ]

    def get_failure_patterns(self) -> list[str]:
        """Return top failure patterns to avoid."""
        with self._lock:
            failure_lessons = [
                l for l in self._lessons
                if l.lesson_type == LessonType.FAILURE_PATTERN
            ]

        failure_lessons = sorted(failure_lessons, key=lambda l: l.confidence, reverse=True)

        return [
            f"[AVOID] {l.observation} → {l.recommendation}"
            for l in failure_lessons[:10]
        ]

    def get_workflow_recommendations(self) -> list[str]:
        """Return workflow optimization recommendations."""
        with self._lock:
            workflow_lessons = [
                l for l in self._lessons
                if l.lesson_type in (
                    LessonType.WORKFLOW_IMPROVEMENT,
                    LessonType.OPTIMIZATION,
                )
            ]

        workflow_lessons = sorted(
            workflow_lessons,
            key=lambda l: (l.impact == "high", l.confidence),
            reverse=True,
        )

        return [
            f"[{l.division.upper()}] {l.recommendation}"
            for l in workflow_lessons[:10]
        ]

    async def generate_prompt_update(self, division: str) -> str | None:
        """Generate a suggested prompt improvement for a division."""
        with self._lock:
            division_lessons = [
                l for l in self._lessons
                if l.division == division and not l.applied
            ]

        if not division_lessons:
            return None

        failures = [l for l in division_lessons if l.lesson_type == LessonType.FAILURE_PATTERN]
        successes = [l for l in division_lessons if l.lesson_type == LessonType.SUCCESS_PATTERN]

        if not failures and not successes:
            return None

        lines = [f"## Suggested Prompt Update for {division.upper()} Division\n"]

        if failures:
            lines.append("### Avoid These Patterns:")
            for f in failures[:3]:
                lines.append(f"- {f.observation}")

        if successes:
            lines.append("\n### Reinforce These Patterns:")
            for s in successes[:3]:
                lines.append(f"- {s.recommendation}")

        lines.append(
            "\n### Recommended Addition to System Prompt:\n"
            f"Always apply the following guidelines for {division} tasks:\n"
        )
        if failures:
            lines.append(f"- Avoid: {failures[0].observation}")
        if successes:
            lines.append(f"- Do: {successes[0].recommendation}")

        return "\n".join(lines)

    def health_check(self) -> ComponentHealth:
        """Return health status of the learning engine."""
        try:
            with self._lock:
                total_lessons = len(self._lessons)
                failures = sum(
                    1 for l in self._lessons
                    if l.lesson_type == LessonType.FAILURE_PATTERN
                )
                successes = sum(
                    1 for l in self._lessons
                    if l.lesson_type == LessonType.SUCCESS_PATTERN
                )

            return ComponentHealth(
                component="learning_engine",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow(),
                metrics={
                    "total_lessons": total_lessons,
                    "success_patterns": successes,
                    "failure_patterns": failures,
                    "repeated_failures_tracked": len(self._failure_pattern_counts),
                },
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="learning_engine",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
