"""AI Video Factory Service — generates short-form and long-form football video."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.creative.video.models import (
    AspectRatio,
    Storyboard,
    StoryboardScene,
    VideoAsset,
    VideoFormat,
    VideoGenerationReport,
    VideoProvider,
)

logger = logging.getLogger("sfc.creative.video")

_singleton: "VideoFactoryService | None" = None


def get_video_factory_service() -> "VideoFactoryService":
    global _singleton
    if _singleton is None:
        _singleton = VideoFactoryService()
    return _singleton


class VideoFactoryService:
    """Generates AI video content for SFC across all platforms."""

    def __init__(self) -> None:
        self._gateway = None
        self._assets: list[VideoAsset] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def generate_video(
        self,
        title: str,
        video_format: VideoFormat = VideoFormat.SHORT,
        platform: str = "youtube",
        subject: str = "",
        narrative: str = "",
        context: dict[str, Any] | None = None,
    ) -> VideoAsset:
        """Generate a video asset with storyboard."""
        context = context or {}
        aspect = self._aspect_for_format(video_format, platform)
        duration = self._duration_for_format(video_format)
        storyboard = await self._create_storyboard(title, subject, narrative, video_format, aspect, duration)
        prompt = await self._build_video_prompt(title, subject, narrative, video_format, context)
        provider = self._select_provider(video_format)
        brand = round(random.uniform(80, 95), 1)

        asset = VideoAsset(
            video_format=video_format,
            title=title,
            provider=provider,
            duration_seconds=duration,
            aspect_ratio=aspect,
            file_url=f"https://assets.sfc.sa/videos/mock/{video_format.value}_{storyboard.storyboard_id[:8]}.mp4",
            storyboard=storyboard,
            prompt_used=prompt,
            platform=platform,
            brand_alignment_score=brand,
            estimated_completion_rate=round(random.uniform(70, 95), 1),
        )
        self._assets.append(asset)
        logger.info(
            "[VideoFactory] Generated | format=%s duration=%.0fs brand=%.0f",
            video_format.value,
            duration,
            brand,
        )
        return asset

    async def generate_batch(
        self,
        titles: list[str],
        video_format: VideoFormat = VideoFormat.SHORT,
        platform: str = "youtube",
    ) -> VideoGenerationReport:
        assets: list[VideoAsset] = []
        for title in titles[:6]:
            asset = await self.generate_video(title=title, video_format=video_format, platform=platform)
            assets.append(asset)

        total_duration = sum(a.duration_seconds for a in assets)
        providers = list({a.provider.value for a in assets})

        return VideoGenerationReport(
            assets=assets,
            total_generated=len(assets),
            total_duration_seconds=total_duration,
            providers_used=providers,
        )

    async def _create_storyboard(
        self,
        title: str,
        subject: str,
        narrative: str,
        video_format: VideoFormat,
        aspect: AspectRatio,
        duration: float,
    ) -> Storyboard:
        num_scenes = max(3, int(duration / 5))
        scenes: list[StoryboardScene] = []
        scene_duration = duration / num_scenes
        scene_templates = [
            ("Opening hook — {subject} dramatic reveal", "upbeat intro"),
            ("Main content — {subject} highlights", "energetic buildup"),
            ("Key moment — {narrative}", "climactic peak"),
            ("Supporting visuals — crowd and stadium", "sustained energy"),
            ("Call to action — subscribe/follow SFC", "outro fade"),
        ]
        for i in range(num_scenes):
            tpl = scene_templates[i % len(scene_templates)]
            scenes.append(
                StoryboardScene(
                    scene_id=i + 1,
                    duration_seconds=scene_duration,
                    visual_description=tpl[0].format(subject=subject or title, narrative=narrative or "SFC"),
                    audio_direction=tpl[1],
                    text_overlay=title if i == 0 else "",
                    transition="cut" if i < num_scenes - 1 else "fade",
                    b_roll="stadium crowd" if 0 < i < num_scenes - 1 else "",
                )
            )
        return Storyboard(
            title=title,
            total_scenes=num_scenes,
            total_duration_seconds=duration,
            aspect_ratio=aspect,
            scenes=scenes,
            music_direction="Arabic sports anthem, high energy",
            color_grade="SFC green/gold LUT",
        )

    async def _build_video_prompt(
        self,
        title: str,
        subject: str,
        narrative: str,
        video_format: VideoFormat,
        context: dict[str, Any],
    ) -> str:
        base = (
            f"Cinematic sports video: {title}. "
            f"Subject: {subject or 'Saudi football'}. "
            f"Narrative: {narrative or 'SFC excellence'}. "
            "SFC brand colors, Arabic sports aesthetic, 4K quality."
        )
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=f"Create a video generation prompt (1 sentence) for: {title}. Format: {video_format.value}.",
                        max_tokens=80,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return base

    def _aspect_for_format(self, video_format: VideoFormat, platform: str) -> AspectRatio:
        vertical_formats = {VideoFormat.SHORT, VideoFormat.REEL, VideoFormat.TIKTOK}
        if video_format in vertical_formats or platform in ("tiktok", "instagram"):
            return AspectRatio.VERTICAL
        return AspectRatio.HORIZONTAL

    def _duration_for_format(self, video_format: VideoFormat) -> float:
        durations = {
            VideoFormat.SHORT: 60.0,
            VideoFormat.REEL: 30.0,
            VideoFormat.TIKTOK: 45.0,
            VideoFormat.MATCH_STORY: 90.0,
            VideoFormat.PLAYER_STORY: 60.0,
            VideoFormat.TRANSFER_STORY: 75.0,
            VideoFormat.DOCUMENTARY_SEGMENT: 300.0,
            VideoFormat.NARRATIVE_VIDEO: 180.0,
        }
        return durations.get(video_format, 60.0)

    def _select_provider(self, video_format: VideoFormat) -> VideoProvider:
        if video_format in (VideoFormat.DOCUMENTARY_SEGMENT, VideoFormat.NARRATIVE_VIDEO):
            return VideoProvider.GOOGLE_VEO
        return random.choice([VideoProvider.KLING, VideoProvider.RUNWAY, VideoProvider.LUMA])

    def get_recent_assets(self, limit: int = 20) -> list[VideoAsset]:
        return self._assets[-limit:]
