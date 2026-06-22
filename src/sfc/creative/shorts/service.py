"""AI Shorts Factory Service — viral short-form content for TikTok/Reels/Shorts."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.creative.shorts.models import (
    ShortsPlatform,
    ShortsPackage,
    ShortsScene,
    ShortsScript,
)

logger = logging.getLogger("sfc.creative.shorts")

_singleton: "ShortsFactoryService | None" = None


def get_shorts_factory_service() -> "ShortsFactoryService":
    global _singleton
    if _singleton is None:
        _singleton = ShortsFactoryService()
    return _singleton


class ShortsFactoryService:
    """Generates platform-optimized short-form video packages."""

    _HASHTAG_POOL = [
        "#SaudiFootball", "#SFC", "#الدوري_السعودي", "#كرة_القدم",
        "#SPL", "#SaudiProLeague", "#Football", "#Soccer",
        "#AlHilal", "#AlNassr", "#Ronaldo", "#WorldCup2034",
    ]

    def __init__(self) -> None:
        self._gateway = None
        self._packages: list[ShortsPackage] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def generate_shorts_package(
        self,
        title: str,
        platform: ShortsPlatform = ShortsPlatform.YOUTUBE_SHORTS,
        narrative: str = "",
        subject: str = "",
        context: dict[str, Any] | None = None,
    ) -> ShortsPackage:
        """Generate a complete short-form video package."""
        context = context or {}
        script = await self._generate_script(title, narrative, subject, platform)
        storyboard = self._create_storyboard(script, title)
        hashtags = self._select_hashtags(platform, subject)
        caption = await self._generate_caption(title, script, platform)
        music = self._select_music(narrative, platform)
        duration = script.estimated_duration_seconds

        package = ShortsPackage(
            title=title,
            platform=platform,
            script=script,
            storyboard=storyboard,
            voiceover_plan=f"Arabic voiceover: {script.hook[:60]}...",
            visual_plan=f"Fast-paced cuts, SFC branding, {platform.value} format",
            caption=caption,
            hashtags=hashtags,
            duration_seconds=duration,
            music_suggestion=music,
            publishing_metadata={
                "platform": platform.value,
                "requires_approval": True,
                "language": "arabic",
            },
        )
        self._packages.append(package)
        logger.info(
            "[ShortsFactory] Generated | platform=%s duration=%.0fs hashtags=%d",
            platform.value,
            duration,
            len(hashtags),
        )
        return package

    async def generate_multi_platform(
        self, title: str, narrative: str = "", subject: str = ""
    ) -> list[ShortsPackage]:
        """Generate shorts package for all 3 platforms."""
        packages: list[ShortsPackage] = []
        for platform in ShortsPlatform:
            package = await self.generate_shorts_package(
                title=title,
                platform=platform,
                narrative=narrative,
                subject=subject,
            )
            packages.append(package)
        return packages

    async def _generate_script(
        self,
        title: str,
        narrative: str,
        subject: str,
        platform: ShortsPlatform,
    ) -> ShortsScript:
        target_duration = {
            ShortsPlatform.YOUTUBE_SHORTS: 58.0,
            ShortsPlatform.TIKTOK: 45.0,
            ShortsPlatform.INSTAGRAM_REELS: 30.0,
        }.get(platform, 45.0)
        word_target = int(target_duration * 2.5)

        hook = ""
        body = ""
        cta = ""

        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Write a {platform.value} short video script for: '{title}'. "
                            f"Narrative: {narrative or subject or 'Saudi football'}. "
                            f"Include: 1) Hook (5 sec), 2) Main content ({int(target_duration-15)} sec), "
                            "3) Call to action (5 sec). Arabic sports style. Be energetic."
                        ),
                        max_tokens=400,
                    )
                )
                full = result.content.strip()
                parts = full.split("\n", 3)
                hook = parts[0] if parts else f"شاهد {subject or title}!"
                body = parts[1] if len(parts) > 1 else narrative or title
                cta = parts[2] if len(parts) > 2 else "تابع SFC للمزيد! 🔔"
            except Exception:
                pass

        if not hook:
            hook = f"شاهد {subject or title} الآن! 🔥"
            body = narrative or f"أبرز اللحظات من {title}. كرة القدم السعودية على أعلى مستوى."
            cta = "اشترك في قناة SFC للمزيد من المحتوى! 👉🔔"

        full_script = f"{hook}\n\n{body}\n\n{cta}"
        word_count = len(full_script.split())
        return ShortsScript(
            hook=hook,
            body=body,
            call_to_action=cta,
            full_script=full_script,
            word_count=word_count,
            estimated_duration_seconds=target_duration,
        )

    def _create_storyboard(self, script: ShortsScript, title: str) -> list[ShortsScene]:
        duration = script.estimated_duration_seconds
        num_scenes = max(5, int(duration / 5))
        scene_duration = duration / num_scenes
        scenes: list[ShortsScene] = []
        for i in range(num_scenes):
            scenes.append(
                ShortsScene(
                    scene_number=i + 1,
                    duration_seconds=scene_duration,
                    visual_description=f"Scene {i+1}: {title[:30]} — dynamic shot",
                    text_overlay=script.hook[:20] if i == 0 else "",
                    audio_note="SFC Arabic voiceover" if i < num_scenes - 1 else "CTA overlay",
                )
            )
        return scenes

    def _select_hashtags(self, platform: ShortsPlatform, subject: str) -> list[str]:
        count = {"youtube_shorts": 5, "tiktok": 8, "instagram_reels": 12}.get(
            platform.value, 6
        )
        base = random.sample(self._HASHTAG_POOL, min(count, len(self._HASHTAG_POOL)))
        if subject:
            base.insert(0, f"#{subject.replace(' ', '')}".replace("##", "#"))
        return base[:count]

    async def _generate_caption(
        self, title: str, script: ShortsScript, platform: ShortsPlatform
    ) -> str:
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Write a {platform.value} caption (2-3 lines) for: '{title}'. "
                            "Arabic, engaging, SFC brand. Include emoji."
                        ),
                        max_tokens=80,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return f"🔥 {title} | SFC — كرة القدم السعودية على أعلى المستويات! 🏆"

    def _select_music(self, narrative: str, platform: ShortsPlatform) -> str:
        tracks = [
            "Arabic sports anthem (upbeat 120 BPM)",
            "Dramatic orchestral buildup",
            "Electronic sports beat (trending)",
            "Traditional Arabic fusion sports",
        ]
        return random.choice(tracks)

    def get_recent_packages(self, limit: int = 20) -> list[ShortsPackage]:
        return self._packages[-limit:]
