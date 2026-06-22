"""Creative Production Orchestrator Service."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.creative.orchestrator.models import (
    AssetRequest,
    ContentFormat,
    ProductionPlan,
    ProductionPriority,
    ProductionTrigger,
)

logger = logging.getLogger("sfc.creative.orchestrator")

_singleton: "CreativeProductionOrchestrator | None" = None


def get_creative_production_orchestrator() -> "CreativeProductionOrchestrator":
    global _singleton
    if _singleton is None:
        _singleton = CreativeProductionOrchestrator()
    return _singleton


class CreativeProductionOrchestrator:
    """Orchestrates all creative production across the media OS."""

    def __init__(self) -> None:
        self._gateway = None
        self._plans: list[ProductionPlan] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def create_production_plan(
        self,
        trigger: ProductionTrigger = ProductionTrigger.SCHEDULED,
        narrative_context: str = "",
        trend_context: str = "",
        war_room_active: bool = False,
        priority: ProductionPriority = ProductionPriority.NORMAL,
        context: dict[str, Any] | None = None,
    ) -> ProductionPlan:
        """Generate a full production plan from intelligence context."""
        context = context or {}
        requests = self._build_asset_requests(
            trigger, narrative_context, trend_context, war_room_active, priority
        )
        briefing = await self._generate_ai_briefing(
            trigger, narrative_context, trend_context, context
        )
        plan = ProductionPlan(
            trigger=trigger,
            asset_requests=requests,
            priority=priority,
            narrative_context=narrative_context,
            trend_context=trend_context,
            war_room_active=war_room_active,
            total_requests=len(requests),
            estimated_production_time_minutes=len(requests) * 3.5,
            persona_assignments=self._assign_personas(requests),
            ai_briefing=briefing,
        )
        self._plans.append(plan)
        logger.info(
            "[CreativeOrchestrator] Plan created | trigger=%s requests=%d",
            trigger.value,
            len(requests),
        )
        return plan

    def _build_asset_requests(
        self,
        trigger: ProductionTrigger,
        narrative: str,
        trend: str,
        war_room: bool,
        priority: ProductionPriority,
    ) -> list[AssetRequest]:
        formats = self._select_formats(trigger, war_room)
        requests: list[AssetRequest] = []
        for fmt in formats:
            title = self._title_for_format(fmt, narrative or trend)
            requests.append(
                AssetRequest(
                    content_format=fmt,
                    title=title,
                    narrative=narrative,
                    platform=self._platform_for_format(fmt),
                    priority=priority,
                    war_room_context=war_room,
                    subject=narrative or trend or "SFC",
                )
            )
        return requests

    def _select_formats(
        self, trigger: ProductionTrigger, war_room: bool
    ) -> list[ContentFormat]:
        if war_room or trigger == ProductionTrigger.WAR_ROOM:
            return [
                ContentFormat.SHORT_VIDEO,
                ContentFormat.IMAGE,
                ContentFormat.THUMBNAIL,
                ContentFormat.THREAD,
            ]
        if trigger == ProductionTrigger.NARRATIVE:
            return [
                ContentFormat.SHORT_VIDEO,
                ContentFormat.PODCAST,
                ContentFormat.IMAGE,
                ContentFormat.SHORTS_PACKAGE,
                ContentFormat.THUMBNAIL,
            ]
        if trigger == ProductionTrigger.TREND:
            return [
                ContentFormat.SHORTS_PACKAGE,
                ContentFormat.SHORT_VIDEO,
                ContentFormat.THREAD,
                ContentFormat.THUMBNAIL,
            ]
        return [
            ContentFormat.IMAGE,
            ContentFormat.AUDIO,
            ContentFormat.SHORT_VIDEO,
            ContentFormat.THUMBNAIL,
        ]

    def _title_for_format(self, fmt: ContentFormat, subject: str) -> str:
        subject = subject or "Saudi Football"
        titles = {
            ContentFormat.SHORT_VIDEO: f"Short: {subject[:40]}",
            ContentFormat.LONG_VIDEO: f"Feature: {subject[:40]}",
            ContentFormat.IMAGE: f"Visual: {subject[:40]}",
            ContentFormat.THUMBNAIL: f"Thumbnail: {subject[:40]}",
            ContentFormat.PODCAST: f"Podcast: {subject[:40]}",
            ContentFormat.THREAD: f"Thread: {subject[:40]}",
            ContentFormat.AUDIO: f"Audio Brief: {subject[:40]}",
            ContentFormat.SHORTS_PACKAGE: f"Shorts: {subject[:40]}",
        }
        return titles.get(fmt, f"{fmt.value}: {subject[:40]}")

    def _platform_for_format(self, fmt: ContentFormat) -> str:
        mapping = {
            ContentFormat.SHORT_VIDEO: "youtube",
            ContentFormat.LONG_VIDEO: "youtube",
            ContentFormat.IMAGE: "instagram",
            ContentFormat.THUMBNAIL: "youtube",
            ContentFormat.PODCAST: "spotify",
            ContentFormat.THREAD: "x",
            ContentFormat.AUDIO: "spotify",
            ContentFormat.SHORTS_PACKAGE: "tiktok",
        }
        return mapping.get(fmt, "multi")

    def _assign_personas(
        self, requests: list[AssetRequest]
    ) -> dict[str, str]:
        personas = ["persona_host_arabic", "persona_analyst", "persona_reporter"]
        return {
            req.request_id: personas[i % len(personas)]
            for i, req in enumerate(requests)
        }

    async def _generate_ai_briefing(
        self,
        trigger: ProductionTrigger,
        narrative: str,
        trend: str,
        context: dict[str, Any],
    ) -> str:
        prompt = (
            f"You are the Creative Director for SFC Saudi football media. "
            f"Generate a concise production briefing (2-3 sentences) for the creative team. "
            f"Trigger: {trigger.value}. "
            f"Narrative: {narrative or 'General SFC content'}. "
            f"Trend: {trend or 'None'}."
        )
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(prompt=prompt, max_tokens=200)
                )
                return result.content.strip()
            except Exception as exc:
                logger.debug("[CreativeOrchestrator] AI briefing fallback: %s", exc)
        return (
            f"Production plan triggered by {trigger.value}. "
            f"Focus: {narrative or trend or 'SFC Saudi football content'}. "
            "All assets must reflect SFC brand guidelines and Arabic-first approach."
        )

    def get_recent_plans(self, limit: int = 10) -> list[ProductionPlan]:
        return self._plans[-limit:]
