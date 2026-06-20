"""Publishing Division — main service implementation."""

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
from sfc.divisions.publishing.interface import PublishingDivisionInterface
from sfc.divisions.publishing.models import PublishingOutput
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, PublishingCompleted
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.publishing.service")

_PLATFORM_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "tiktok":            {"max_chars": 500,   "hashtag_limit": 10, "peak_time_utc": "19:00"},
    "instagram_reels":   {"max_chars": 2200,  "hashtag_limit": 30, "peak_time_utc": "18:00"},
    "instagram_stories": {"max_chars": 200,   "hashtag_limit": 10, "peak_time_utc": "08:00"},
    "instagram_feed":    {"max_chars": 2200,  "hashtag_limit": 30, "peak_time_utc": "18:00"},
    "youtube_shorts":    {"max_chars": 500,   "hashtag_limit": 15, "peak_time_utc": "14:00"},
    "youtube":           {"max_chars": 5000,  "hashtag_limit": 500, "peak_time_utc": "15:00"},
    "x":                 {"max_chars": 280,   "hashtag_limit": 2,  "peak_time_utc": "12:00"},
    "telegram":          {"max_chars": 4096,  "hashtag_limit": 0,  "peak_time_utc": "20:00"},
    "whatsapp":          {"max_chars": 1024,  "hashtag_limit": 0,  "peak_time_utc": "20:00"},
    "website":           {"max_chars": 100000,"hashtag_limit": 0,  "peak_time_utc": "09:00"},
    "newsletter":        {"max_chars": 50000, "hashtag_limit": 0,  "peak_time_utc": "07:00"},
}


class PublishingService(PublishingDivisionInterface):
    """Publishing Division — multi-platform content distribution."""

    division = Division.PUBLISHING

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0
        self._total_published = 0

    async def initialize(self) -> None:
        logger.info("[Publishing] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Publishing] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            approved_content = state.get("approved_content", [])
            rejected_count = len(state.get("rejected_content", []))
            revenue_signals = state.get("revenue_signals", [])
            plan = state.get("execution_plan", {})

            if not approved_content:
                return PublishingOutput(
                    run_id=input.run_id,
                    division=self.division.value,
                    success=True,
                    data={
                        "publish_queue": [],
                        "publish_results": {
                            "published_count": 0,
                            "rejected_count": rejected_count,
                            "status": "nothing_to_publish",
                        },
                        "pipeline_stage": "publishing_complete",
                    },
                    processing_time_ms=(time.monotonic() - start) * 1000,
                    publish_results={"published_count": 0, "status": "nothing_to_publish"},
                )

            pub_plan = await self.create_publishing_plan(approved_content, plan)
            queue = pub_plan.get("queue", [])
            platform_results: dict[str, list[dict[str, Any]]] = {}

            for job in queue:
                platform = job["platform"]
                if platform not in platform_results:
                    platform_results[platform] = []
                platform_results[platform].append({
                    "job_id": job["job_id"],
                    "content_id": job.get("content_id"),
                    "status": "queued",
                })

            self._total_published += len(approved_content)

            events: list[BaseEvent] = [
                PublishingCompleted(
                    division=self.division.value,
                    run_id=input.run_id,
                    payload={
                        "published_count": len(approved_content),
                        "job_count": len(queue),
                        "platform_count": len(platform_results),
                    },
                )
            ]

            if self.memory:
                self.memory.set(f"queue_{input.run_id}", queue)

            get_event_bus().publish_many(events)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            results = {
                "published_count": len(approved_content),
                "job_count": len(queue),
                "rejected_count": rejected_count,
                "platform_results": platform_results,
                "status": "queued",
                "completed_at": datetime.utcnow().isoformat(),
            }

            return PublishingOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={
                    "publish_queue": queue,
                    "publish_results": results,
                    "pipeline_stage": "publishing_complete",
                },
                events_to_publish=events,
                processing_time_ms=elapsed,
                publish_queue=queue,
                publish_results=results,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Publishing] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def create_publishing_plan(
        self, approved_content: list[dict[str, Any]], plan: dict[str, Any]
    ) -> dict[str, Any]:
        queue: list[dict[str, Any]] = []
        for content in approved_content:
            platforms = content.get("platforms", [])
            for platform in platforms:
                adapted = await self.apply_platform_constraints(content, platform)
                optimal_time = await self.estimate_optimal_time(
                    platform, plan.get("task_type", "news")
                )
                queue.append({
                    "job_id": str(uuid.uuid4()),
                    "content_id": content.get("content_id"),
                    "platform": platform,
                    "title": adapted.get("title", ""),
                    "body_preview": adapted.get("body", ""),
                    "char_count": adapted.get("char_count", 0),
                    "optimal_publish_time": optimal_time,
                    "status": "queued",
                    "queued_at": datetime.utcnow().isoformat(),
                })
        return {"queue": queue, "total_jobs": len(queue)}

    async def apply_platform_constraints(
        self, content: dict[str, Any], platform: str
    ) -> dict[str, Any]:
        constraints = _PLATFORM_CONSTRAINTS.get(platform, {"max_chars": 280, "hashtag_limit": 2})
        body = content.get("body", "")
        max_chars = constraints["max_chars"]
        truncated = body[:max_chars]
        return {
            "title": content.get("title", "")[:100],
            "body": truncated,
            "char_count": len(truncated),
            "platform": platform,
            "constraints_applied": True,
        }

    async def estimate_optimal_time(self, platform: str, task_type: str) -> str:
        # Crisis content bypasses scheduling — publish immediately
        if task_type == "crisis":
            return datetime.utcnow().isoformat()
        constraints = _PLATFORM_CONSTRAINTS.get(platform, {})
        return constraints.get("peak_time_utc", "18:00")

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.publishing.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        reasons: list[str] = []
        if not content.get("platform"):
            reasons.append("Missing platform")
        if not content.get("title"):
            reasons.append("Missing title")
        return ValidationResult(valid=len(reasons) == 0, score=100.0 - len(reasons) * 20.0, reasons=reasons)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={"total_published": self._total_published, "call_count": self._call_count},
            highlights=[f"{self._total_published} content pieces distributed"],
            recommendations=["Implement platform API rate-limit monitoring"],
        )

    def health_check(self) -> DivisionHealth:
        return DivisionHealth(
            division=self.division.value,
            status="healthy",
            metrics={"call_count": self._call_count, "total_published": self._total_published},
        )

    def describe(self) -> str:
        return "Multi-platform content distribution and scheduling"
