"""Creative Division — generates video, image, audio, and graphic assets."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from core.models import Division, EventType, Platform, SFCEvent
from divisions.base import BaseDivision

ASSET_SPECS: dict[str, dict[str, Any]] = {
    "tiktok_video": {"aspect_ratio": "9:16", "max_duration_s": 60, "format": "mp4"},
    "instagram_reel": {"aspect_ratio": "9:16", "max_duration_s": 90, "format": "mp4"},
    "youtube_short": {"aspect_ratio": "9:16", "max_duration_s": 60, "format": "mp4"},
    "youtube_long": {"aspect_ratio": "16:9", "min_duration_s": 60, "format": "mp4"},
    "thumbnail": {"dimensions": "1280x720", "format": "jpg"},
    "poster": {"dimensions": "1080x1920", "format": "jpg"},
    "instagram_feed": {"dimensions": "1080x1080", "format": "jpg"},
    "voiceover": {"format": "mp3", "provider": "elevenlabs"},
}


class CreativeDivision(BaseDivision):
    """Produces multimedia creative assets.

    Capabilities:
    - Video generation (Veo, Kling, Runway, Luma)
    - Image generation (thumbnails, posters, graphics)
    - Voice generation (ElevenLabs)
    - Podcast production
    """

    division = Division.CREATIVE

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        handlers = {
            EventType.CONTENT_CREATED: self._produce_creative_assets,
            EventType.MATCH_STARTED: self._prepare_match_graphics,
        }
        handler = handlers.get(EventType(event.event_type))
        if handler:
            return await handler(event)
        return None

    async def _produce_creative_assets(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        content_id = payload.get("content_id", str(uuid4()))
        platforms = payload.get("platforms", [])
        assets: list[dict[str, Any]] = []

        for platform_str in platforms:
            spec = self._get_spec_for_platform(platform_str)
            if spec:
                asset = self._create_asset_brief(content_id, platform_str, spec)
                assets.append(asset)
                self.memory.set(f"asset:{asset['asset_id']}", asset)

        self.logger.info("Created %d asset briefs for content %s", len(assets), content_id)
        return {"content_id": content_id, "assets_briefed": len(assets), "assets": assets}

    async def _prepare_match_graphics(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        home = payload.get("home_team", "Home")
        away = payload.get("away_team", "Away")
        brief_id = str(uuid4())
        brief = {
            "brief_id": brief_id,
            "type": "match_preview_graphic",
            "spec": ASSET_SPECS["poster"],
            "copy": f"{home} vs {away}",
            "urgency": "high",
        }
        self.memory.set(f"asset:{brief_id}", brief)
        return {"brief_id": brief_id, "status": "briefed"}

    def _get_spec_for_platform(self, platform: str) -> dict[str, Any] | None:
        mapping = {
            "tiktok": "tiktok_video",
            "instagram_reels": "instagram_reel",
            "youtube_shorts": "youtube_short",
            "youtube": "youtube_long",
            "instagram_feed": "instagram_feed",
        }
        spec_key = mapping.get(platform)
        return ASSET_SPECS.get(spec_key, {}) if spec_key else None

    def _create_asset_brief(
        self, content_id: str, platform: str, spec: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "asset_id": str(uuid4()),
            "content_id": content_id,
            "platform": platform,
            "spec": spec,
            "status": "briefed",
            "provider": self._select_provider(spec),
        }

    def _select_provider(self, spec: dict[str, Any]) -> str:
        fmt = spec.get("format", "")
        if fmt == "mp4":
            return "veo"
        if fmt == "mp3":
            return "elevenlabs"
        return "internal"

    def generate_thumbnail_brief(self, title: str, content_id: str) -> dict[str, Any]:
        brief = {
            "asset_id": str(uuid4()),
            "content_id": content_id,
            "type": "thumbnail",
            "spec": ASSET_SPECS["thumbnail"],
            "copy": title,
            "status": "briefed",
        }
        self.memory.set(f"asset:{brief['asset_id']}", brief)
        return brief
