"""Pika Labs video provider.

API: https://api.pika.art/v1/generate
Auth: Bearer PIKA_API_KEY
Flow: POST to generate → poll status until completed
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.ai_video.providers.base import AIVideoProvider

logger = logging.getLogger("sfc.connectors.ai_video.pika")

_BASE = "https://api.pika.art/v1"
_POLL_INTERVAL = 10
_POLL_TIMEOUT = 300


class PikaVideoProvider(AIVideoProvider):
    """Pika Labs text-to-video."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("PIKA_API_KEY", "")

    @property
    def name(self) -> str:
        return "pika"

    @property
    def is_enabled(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def generate(self, scene) -> AIVideoResult:
        if not self.is_enabled:
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.SKIPPED,
                error_message="PIKA_API_KEY not set",
            )

        try:
            import httpx

            ratio = "16:9" if scene.aspect_ratio == "16:9" else "9:16"
            payload = {
                "promptText": scene.visual_prompt,
                "negativePrompt": scene.negative_prompt,
                "options": {
                    "aspectRatio": ratio,
                    "frameRate": 24,
                    "camera": {"zoom": "none", "pan": "none", "tilt": "none"},
                    "extend": False,
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{_BASE}/generate",
                    headers=self._headers(),
                    json=payload,
                )

            if resp.status_code not in (200, 201):
                logger.warning("[Pika] Create generation HTTP %d: %s", resp.status_code, resp.text[:200])
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            job_id = data.get("id", "") or data.get("job_id", "")
            if not job_id:
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message="No id in response",
                )

            return await self._poll(job_id, scene.scene_id, scene.duration_seconds)

        except Exception as exc:
            logger.error("[Pika] generate failed scene=%s: %s", scene.scene_id, exc)
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.FAILED,
                error_message=str(exc),
            )

    async def _poll(self, job_id: str, scene_id: str, duration: float) -> AIVideoResult:
        import httpx

        waited = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            while waited < _POLL_TIMEOUT:
                resp = await client.get(
                    f"{_BASE}/jobs/{job_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")
                    if status in ("completed", "finished", "succeeded"):
                        videos = data.get("videos", []) or []
                        public_url = videos[0].get("url", "") if videos else data.get("url", "")
                        logger.info("[Pika] Job %s completed url=%s", job_id, public_url)
                        return AIVideoResult(
                            task_id=job_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.COMPLETED,
                            public_url=public_url,
                            duration_seconds=duration,
                        )
                    if status in ("failed", "error"):
                        msg = data.get("error", "Unknown error")
                        logger.warning("[Pika] Job %s failed: %s", job_id, msg)
                        return AIVideoResult(
                            task_id=job_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.FAILED,
                            error_message=msg,
                        )

                await asyncio.sleep(_POLL_INTERVAL)
                waited += _POLL_INTERVAL

        logger.warning("[Pika] Timed out polling job %s after %ds", job_id, _POLL_TIMEOUT)
        return AIVideoResult(
            task_id=job_id,
            provider=self.name,
            scene_id=scene_id,
            status=AIVideoStatus.FAILED,
            error_message=f"Timed out after {_POLL_TIMEOUT}s",
        )
