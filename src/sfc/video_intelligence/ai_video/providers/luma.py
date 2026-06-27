"""Luma Dream Machine video provider.

API: https://api.lumalabs.ai/dream-machine/v1/generations
Auth: Bearer LUMA_API_KEY
Flow: POST → {id} → poll GET /generations/{id} until state == "completed"
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.ai_video.providers.base import AIVideoProvider

logger = logging.getLogger("sfc.connectors.ai_video.luma")

_BASE = "https://api.lumalabs.ai/dream-machine/v1/generations"
_POLL_INTERVAL = 10
_POLL_TIMEOUT = 300


class LumaVideoProvider(AIVideoProvider):
    """Luma Dream Machine text-to-video."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("LUMA_API_KEY", "")

    @property
    def name(self) -> str:
        return "luma"

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
                error_message="LUMA_API_KEY not set",
            )

        try:
            import httpx

            payload: dict = {
                "prompt": scene.visual_prompt,
                "aspect_ratio": "16:9" if scene.aspect_ratio == "16:9" else "9:16",
                "loop": False,
            }
            if scene.reference_image_url:
                payload["keyframes"] = {
                    "frame0": {"type": "image", "url": scene.reference_image_url}
                }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    _BASE,
                    headers=self._headers(),
                    json=payload,
                )

            if resp.status_code not in (200, 201):
                logger.warning("[Luma] Create generation HTTP %d: %s", resp.status_code, resp.text[:200])
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

            gen_id = resp.json().get("id", "")
            if not gen_id:
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message="No id in response",
                )

            return await self._poll(gen_id, scene.scene_id, scene.duration_seconds)

        except Exception as exc:
            logger.error("[Luma] generate failed scene=%s: %s", scene.scene_id, exc)
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.FAILED,
                error_message=str(exc),
            )

    async def _poll(self, gen_id: str, scene_id: str, duration: float) -> AIVideoResult:
        import httpx

        waited = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            while waited < _POLL_TIMEOUT:
                resp = await client.get(
                    f"{_BASE}/{gen_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    state = data.get("state", "")
                    if state == "completed":
                        assets = data.get("assets", {}) or {}
                        public_url = assets.get("video", "")
                        logger.info("[Luma] Generation %s completed url=%s", gen_id, public_url)
                        return AIVideoResult(
                            task_id=gen_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.COMPLETED,
                            public_url=public_url,
                            duration_seconds=duration,
                        )
                    if state == "failed":
                        msg = data.get("failure_reason", "Unknown error")
                        logger.warning("[Luma] Generation %s failed: %s", gen_id, msg)
                        return AIVideoResult(
                            task_id=gen_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.FAILED,
                            error_message=msg,
                        )

                await asyncio.sleep(_POLL_INTERVAL)
                waited += _POLL_INTERVAL

        logger.warning("[Luma] Timed out polling generation %s after %ds", gen_id, _POLL_TIMEOUT)
        return AIVideoResult(
            task_id=gen_id,
            provider=self.name,
            scene_id=scene_id,
            status=AIVideoStatus.FAILED,
            error_message=f"Timed out after {_POLL_TIMEOUT}s",
        )
