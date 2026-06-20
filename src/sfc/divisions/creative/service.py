"""Creative Division — main service implementation."""

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
from sfc.divisions.creative.interface import CreativeDivisionInterface
from sfc.divisions.creative.models import CreativeOutput
from sfc.events.bus import get_event_bus
from sfc.events.types import AssetBriefCreated, BaseEvent
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.creative.service")

_ASSET_SPECS: dict[str, dict[str, Any]] = {
    "tiktok_video": {"aspect_ratio": "9:16", "max_duration_s": 60, "format": "mp4", "provider": "veo"},
    "instagram_reel": {"aspect_ratio": "9:16", "max_duration_s": 90, "format": "mp4", "provider": "veo"},
    "youtube_short": {"aspect_ratio": "9:16", "max_duration_s": 60, "format": "mp4", "provider": "kling"},
    "youtube_long": {"aspect_ratio": "16:9", "format": "mp4", "provider": "runway"},
    "thumbnail": {"dimensions": "1280x720", "format": "jpg", "provider": "internal"},
    "poster": {"dimensions": "1080x1920", "format": "jpg", "provider": "internal"},
    "instagram_feed": {"dimensions": "1080x1080", "format": "jpg", "provider": "internal"},
    "voiceover": {"format": "mp3", "provider": "elevenlabs"},
    "social_graphic": {"dimensions": "1200x675", "format": "jpg", "provider": "internal"},
}

_PLATFORM_TO_ASSET: dict[str, list[str]] = {
    "tiktok": ["tiktok_video", "voiceover"],
    "instagram_reels": ["instagram_reel", "voiceover"],
    "instagram_stories": ["instagram_reel"],
    "instagram_feed": ["instagram_feed"],
    "youtube_shorts": ["youtube_short", "thumbnail"],
    "youtube": ["youtube_long", "thumbnail", "voiceover"],
    "x": ["social_graphic"],
    "telegram": ["social_graphic"],
    "website": ["thumbnail", "social_graphic"],
    "whatsapp": ["social_graphic"],
    "newsletter": ["social_graphic"],
}

_PROVIDER_HOURS: dict[str, float] = {
    "veo": 2.0, "kling": 1.5, "runway": 3.0,
    "elevenlabs": 0.5, "internal": 0.25,
}


class CreativeService(CreativeDivisionInterface):
    """Creative Division — multimedia asset briefs and production coordination."""

    division = Division.CREATIVE

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0

    async def initialize(self) -> None:
        logger.info("[Creative] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Creative] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            content_drafts = state.get("content_drafts", [])

            if not content_drafts:
                return DivisionOutput(
                    run_id=input.run_id,
                    division=self.division.value,
                    success=True,
                    data={"creative_assets": [], "warnings": ["No drafts to process"]},
                    processing_time_ms=(time.monotonic() - start) * 1000,
                )

            assets: list[dict[str, Any]] = []
            events: list[BaseEvent] = []

            for draft in content_drafts:
                platforms = draft.get("platforms", [])
                brief = await self.create_asset_brief(draft, platforms)
                assets.extend(brief.get("assets", []))
                events.append(AssetBriefCreated(
                    division=self.division.value,
                    run_id=input.run_id,
                    payload={"asset_count": len(brief.get("assets", [])), "platforms": platforms},
                ))

            production_time = await self.calculate_production_time(assets)

            if self.memory:
                self.memory.set(f"assets_{input.run_id}", assets)

            get_event_bus().publish_many(events)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return CreativeOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={
                    "creative_assets": assets,
                    "estimated_production_hours": production_time,
                    "pipeline_stage": "creative_complete",
                },
                events_to_publish=events,
                processing_time_ms=elapsed,
                creative_assets=assets,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Creative] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def create_asset_brief(
        self, content_draft: dict[str, Any], platforms: list[str]
    ) -> dict[str, Any]:
        assets: list[dict[str, Any]] = []
        for platform in platforms:
            asset_types = _PLATFORM_TO_ASSET.get(platform, ["social_graphic"])
            for asset_type_key in asset_types:
                spec = _ASSET_SPECS.get(asset_type_key, {})
                provider = await self.assign_producer(asset_type_key)
                asset = {
                    "asset_id": str(uuid.uuid4()),
                    "content_id": content_draft.get("content_id"),
                    "asset_type": asset_type_key,
                    "platform": platform,
                    "spec": spec,
                    "provider": provider,
                    "copy": {
                        "title": content_draft.get("title", ""),
                        "body_preview": content_draft.get("body", "")[:150],
                        "is_rumor": content_draft.get("is_rumor", False),
                    },
                    "status": "briefed",
                    "briefed_at": datetime.utcnow().isoformat(),
                }
                assets.append(asset)
        return {"assets": assets, "platform_count": len(platforms)}

    async def assign_producer(self, asset_type: str) -> str:
        spec = _ASSET_SPECS.get(asset_type, {})
        return spec.get("provider", "internal")

    async def calculate_production_time(self, assets: list[dict[str, Any]]) -> float:
        total = sum(_PROVIDER_HOURS.get(a.get("provider", "internal"), 0.25) for a in assets)
        return round(total, 2)

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.creative.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        reasons: list[str] = []
        if not content.get("asset_type"):
            reasons.append("Missing asset_type")
        if not content.get("platform"):
            reasons.append("Missing platform")
        return ValidationResult(valid=len(reasons) == 0, score=90.0 - len(reasons) * 10.0, reasons=reasons)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={"total_calls": self._call_count, "error_count": self._error_count},
            highlights=[f"{self._call_count} asset production runs completed"],
            recommendations=["Expand Veo and Kling usage for TikTok-native content"],
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
        return "Multimedia asset production briefs — video, graphics, voiceover"
