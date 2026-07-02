"""AI Video Generation Service — orchestrates the provider chain.

Provider order: Kling → Runway → Luma → Pika (try next on failure).
Scenes are generated in parallel for maximum throughput.

Persistence: provider result URLs are temporary signed URLs that expire
within hours. Every successful generation is downloaded to local disk
(CLIP_STORAGE_ROOT/ai_video/) and re-uploaded to R2/S3 when configured,
so downstream rendering has a local file and publishing has a durable URL.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.shared.constants import CLIP_STORAGE_ROOT

if TYPE_CHECKING:
    from sfc.video_intelligence.ai_video.providers.base import AIVideoProvider
    from sfc.video_intelligence.storyboard.models import Storyboard, StoryboardScene

logger = logging.getLogger("sfc.video_intelligence.ai_video")

_DOWNLOAD_TIMEOUT = 120.0

_singleton: "AIVideoGenerationService | None" = None


def get_ai_video_generation_service() -> "AIVideoGenerationService":
    global _singleton
    if _singleton is None:
        _singleton = AIVideoGenerationService()
    return _singleton


class AIVideoGenerationService:
    """Tries providers in order; generates all scenes in parallel."""

    def __init__(self) -> None:
        from sfc.video_intelligence.ai_video.providers.kling import KlingVideoProvider
        from sfc.video_intelligence.ai_video.providers.runway import RunwayVideoProvider
        from sfc.video_intelligence.ai_video.providers.luma import LumaVideoProvider
        from sfc.video_intelligence.ai_video.providers.pika import PikaVideoProvider

        self._providers: list["AIVideoProvider"] = [
            KlingVideoProvider(),
            RunwayVideoProvider(),
            LumaVideoProvider(),
            PikaVideoProvider(),
        ]

    @property
    def enabled_providers(self) -> list["AIVideoProvider"]:
        return [p for p in self._providers if p.is_enabled]

    @property
    def any_provider_enabled(self) -> bool:
        return bool(self.enabled_providers)

    async def generate_scene(self, scene: "StoryboardScene") -> AIVideoResult:
        """Try providers in order until one succeeds."""
        providers = self.enabled_providers
        if not providers:
            logger.warning("[AIVideo] No AI video providers configured for scene=%s", scene.scene_id)
            return AIVideoResult(
                provider="none",
                scene_id=scene.scene_id,
                status=AIVideoStatus.SKIPPED,
                error_message="No AI video providers configured",
            )

        last_result: AIVideoResult | None = None
        for provider in providers:
            try:
                result = await provider.generate(scene)
                if result.succeeded:
                    logger.info(
                        "[AIVideo] scene=%s provider=%s status=%s url=%s",
                        scene.scene_id, provider.name, result.status.value, result.public_url,
                    )
                    return await self._persist(result)
                logger.warning(
                    "[AIVideo] scene=%s provider=%s failed: %s — trying next",
                    scene.scene_id, provider.name, result.error_message,
                )
                last_result = result
            except Exception as exc:
                logger.error(
                    "[AIVideo] scene=%s provider=%s exception: %s — trying next",
                    scene.scene_id, provider.name, exc,
                )
                last_result = AIVideoResult(
                    provider=provider.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message=str(exc),
                )

        return last_result or AIVideoResult(
            provider="all_failed",
            scene_id=scene.scene_id,
            status=AIVideoStatus.FAILED,
            error_message="All providers failed",
        )

    async def generate_video(self, storyboard: "Storyboard") -> list[AIVideoResult]:
        """Generate all scenes in parallel."""
        tasks = [self.generate_scene(scene) for scene in storyboard.scenes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[AIVideoResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                scene_id = storyboard.scenes[i].scene_id if i < len(storyboard.scenes) else "unknown"
                logger.error("[AIVideo] Scene %s raised exception: %s", scene_id, r)
                output.append(AIVideoResult(
                    provider="error",
                    scene_id=scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message=str(r),
                ))
            else:
                output.append(r)

        succeeded = sum(1 for r in output if r.succeeded)
        logger.info(
            "[AIVideo] storyboard=%s scenes=%d succeeded=%d",
            storyboard.storyboard_id, len(output), succeeded,
        )
        return output

    async def _persist(self, result: AIVideoResult) -> AIVideoResult:
        """Download the provider's temporary URL to disk; re-upload for a durable URL.

        Best-effort: on any failure the result keeps the provider URL so the
        pipeline still has *something* to publish before it expires.
        """
        if result.local_path or not result.public_url:
            return result

        local_dir = Path(CLIP_STORAGE_ROOT) / "ai_video"
        local_path = local_dir / f"{result.scene_id or result.task_id}_{result.provider}.mp4"

        try:
            import httpx

            local_dir.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient(
                timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True
            ) as client:
                async with client.stream("GET", result.public_url) as resp:
                    resp.raise_for_status()
                    with open(local_path, "wb") as fh:
                        async for chunk in resp.aiter_bytes(chunk_size=1 << 20):
                            fh.write(chunk)
            result.local_path = str(local_path)
            logger.info("[AIVideo] Downloaded scene=%s → %s", result.scene_id, local_path)
        except Exception as exc:
            logger.warning(
                "[AIVideo] Download failed scene=%s (keeping provider URL): %s",
                result.scene_id, exc,
            )
            return result

        # Provider URLs expire — swap in a durable R2/S3 URL when storage is configured
        try:
            from sfc.storage.service import get_clip_storage_service

            storage = get_clip_storage_service()
            durable = storage.upload(
                result.local_path, object_key=f"ai_video/{local_path.name}"
            )
            if durable:
                result.public_url = durable
        except Exception as exc:
            logger.warning("[AIVideo] Durable upload failed scene=%s: %s", result.scene_id, exc)

        return result

    def reset_for_test(self) -> None:
        pass
