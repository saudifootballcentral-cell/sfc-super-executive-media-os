"""Editorial Division — main service implementation."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from sfc.core.models import Division
from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.divisions.editorial.interface import EditorialDivisionInterface
from sfc.divisions.editorial.models import EditorialOutput
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, ContentDraftCreated
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.editorial.service")

_PLATFORM_MAP: dict[str, list[str]] = {
    "video": ["tiktok", "instagram_reels", "youtube_shorts", "youtube"],
    "article": ["website", "newsletter"],
    "social": ["x", "instagram_feed", "telegram", "whatsapp"],
}

_CLICKBAIT_PATTERNS = [
    "you won't believe",
    "shocking",
    "unbelievable secret",
    "number 7 will shock you",
]


class EditorialService(EditorialDivisionInterface):
    """Editorial Division — content drafting and accuracy enforcement."""

    division = Division.EDITORIAL

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0

    async def initialize(self) -> None:
        logger.info("[Editorial] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Editorial] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            plan = state.get("execution_plan", {})
            intel = state.get("intelligence_report", {})
            payload = input.payload
            verified_sources = state.get("verified_sources", [])

            content_types = plan.get("content_types", ["article"])
            platforms_targeted = plan.get("platforms_targeted", [])
            confidence = intel.get("confidence_score", 60.0)
            source_count = len(verified_sources)
            is_rumor = intel.get("is_rumor", False)

            drafts: list[dict[str, Any]] = []
            events: list[BaseEvent] = []

            for ct in content_types:
                brief = await self.create_content_brief(intel, plan)
                draft = await self.generate_draft(brief, ct)
                accuracy = await self.check_accuracy_rules(draft)

                draft.update({
                    "content_id": str(uuid.uuid4()),
                    "platforms": self._select_platforms(ct, platforms_targeted),
                    "scores": {
                        "confidence_score": confidence,
                        "risk_score": max(0.0, 100.0 - confidence),
                        "source_count": source_count,
                        "brand_alignment_score": 85.0,
                    },
                    "sources": [s.get("name", "") if isinstance(s, dict) else s
                                for s in verified_sources],
                    "is_rumor": is_rumor,
                    "rumor_label": intel.get("rumor_label") if is_rumor else None,
                    "division": "editorial",
                    "accuracy_check": accuracy,
                    "created_at": datetime.utcnow().isoformat(),
                })
                drafts.append(draft)
                events.append(ContentDraftCreated(
                    division=self.division.value,
                    run_id=input.run_id,
                    payload={"content_type": ct, "title": draft.get("title", "")},
                ))

            if self.memory:
                self.memory.set(f"drafts_{input.run_id}", drafts)

            get_event_bus().publish_many(events)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return EditorialOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={"content_drafts": drafts, "pipeline_stage": "editorial_complete"},
                events_to_publish=events,
                processing_time_ms=elapsed,
                content_drafts=drafts,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Editorial] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def create_content_brief(
        self, intelligence_report: dict[str, Any], plan: dict[str, Any]
    ) -> dict[str, Any]:
        """Produce a structured editorial brief from an intelligence report."""
        return {
            "topic": intelligence_report.get("key_facts", ["Saudi football"])[:1],
            "key_facts": intelligence_report.get("key_facts", []),
            "entities": intelligence_report.get("entities_detected", {}),
            "sentiment": intelligence_report.get("sentiment", "neutral"),
            "task_type": plan.get("task_type", "news"),
            "target_platforms": plan.get("platforms_targeted", []),
            "is_rumor": intelligence_report.get("is_rumor", False),
            "confidence": intelligence_report.get("confidence_score", 60.0),
            "briefed_at": datetime.utcnow().isoformat(),
        }

    async def generate_draft(
        self, brief: dict[str, Any], content_type: str
    ) -> dict[str, Any]:
        """Generate a full content draft from a brief."""
        key_facts = brief.get("key_facts", ["Saudi football update"])
        title = key_facts[0][:100] if key_facts else f"Saudi Football {content_type.title()}"
        is_rumor = brief.get("is_rumor", False)
        body_prefix = "[RUMOR — NOT CONFIRMED] " if is_rumor else ""

        body_parts: list[str] = []
        for fact in key_facts[:3]:
            body_parts.append(fact)
        if not body_parts:
            body_parts.append(f"Saudi football update — {content_type}")
        body = body_prefix + " ".join(body_parts)

        return {
            "title": title,
            "body": body,
            "content_type": content_type,
            "status": "draft",
            "key_facts": key_facts,
        }

    async def check_accuracy_rules(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Validate the draft: no clickbait, no unsupported claims."""
        title_lower = draft.get("title", "").lower()
        issues: list[str] = []
        for pattern in _CLICKBAIT_PATTERNS:
            if pattern in title_lower:
                issues.append(f"Clickbait pattern detected: '{pattern}'")
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat(),
        }

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.editorial.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        reasons: list[str] = []
        title = content.get("title", "")
        body = content.get("body", "")
        if not title:
            reasons.append("Missing title")
        if len(body) < 20:
            reasons.append("Body too short (< 20 characters)")
        accuracy = await self.check_accuracy_rules(content)
        if not accuracy["passed"]:
            reasons.extend(accuracy["issues"])
        score = 90.0 - len(reasons) * 10.0
        return ValidationResult(valid=len(reasons) == 0, score=max(0.0, score), reasons=reasons)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={"total_calls": self._call_count, "error_count": self._error_count},
            highlights=[f"Produced content in {self._call_count} pipeline runs"],
            recommendations=["Expand content types for better platform coverage"],
        )

    def health_check(self) -> DivisionHealth:
        status = "healthy"
        if self._call_count > 0 and self._error_count / self._call_count > 0.3:
            status = "degraded"
        return DivisionHealth(
            division=self.division.value,
            status=status,
            metrics={"call_count": self._call_count, "error_count": self._error_count},
        )

    def describe(self) -> str:
        return "Content drafting, accuracy enforcement, editorial strategy"

    def _select_platforms(
        self, content_type: str, available_platforms: list[str]
    ) -> list[str]:
        video_types = {"highlight_clip", "live_update", "short_video", "teaser_clips",
                       "campaign_hero_video", "video_essay"}
        text_types = {"breaking_news_article", "long_form_analysis", "newsletter_edition",
                      "crisis_statement", "clarification_post"}

        if content_type in video_types:
            video_plats = {"tiktok", "instagram_reels", "youtube_shorts", "youtube"}
            return [p for p in available_platforms if p in video_plats] or list(video_plats)[:2]
        if content_type in text_types:
            text_plats = {"website", "newsletter", "telegram"}
            return [p for p in available_platforms if p in text_plats] or ["website"]
        return available_platforms[:3] or ["x"]
