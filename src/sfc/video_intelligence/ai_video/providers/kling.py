"""Kling AI video provider.

API: https://api.klingai.com/v1/videos/text2video
Auth: Bearer KLING_API_KEY
Flow: POST to create task → poll GET /{task_id} until task_status == "succeed"
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.ai_video.providers.base import AIVideoProvider

if TYPE_CHECKING := False:
    pass

logger = logging.getLogger("sfc.connectors.ai_video.kling")

_BASE_URL = "https://api.klingai.com/v1/videos/text2video"
_POLL_INTERVAL = 10
_POLL_TIMEOUT = 300


class KlingVideoProvider(AIVideoProvider):
    """Kling text-to-video via REST API."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("KLING_API_KEY", "")

    @property
    def name(self) -> str:
        return "kling"

    @property
    def is_enabled(self) -> bool:
        return bool(self._api_key)

    async def generate(self, scene) -> AIVideoResult:
        if not self.is_enabled:
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.SKIPPED,
                error_message="KLING_API_KEY not set",
            )

        try:
            import httpx

            duration = min(int(scene.duration_seconds), 10)  # Kling max 10s
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    _BASE_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "prompt": scene.visual_prompt,
                        "negative_prompt": scene.negative_prompt,
                        "cfg_scale": 0.5,
                        "mode": "std",
                        "duration": str(duration),
                        "aspect_ratio": "16:9" if scene.aspect_ratio == "16:9" else "9:16",
                    },
                )

            if resp.status_code != 200:
                logger.warning("[Kling] Create task HTTP %d: %s", resp.status_code, resp.text[:200])
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            task_id = (data.get("data", {}) or {}).get("task_id", "")
            if not task_id:
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message="No task_id in response",
                )

            return await self._poll(task_id, scene.scene_id)

        except Exception as exc:
            logger.error("[Kling] generate failed scene=%s: %s", scene.scene_id, exc)
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.FAILED,
                error_message=str(exc),
            )

    async def _poll(self, task_id: str, scene_id: str) -> AIVideoResult:
        import httpx

        waited = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            while waited < _POLL_TIMEOUT:
                resp = await client.get(
                    f"{_BASE_URL}/{task_id}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {}) or {}
                    status = data.get("task_status", "")
                    if status == "succeed":
                        works = data.get("task_result", {}).get("videos", [])
                        public_url = works[0].get("url", "") if works else ""
                        duration = works[0].get("duration", 0.0) if works else 0.0
                        logger.info("[Kling] Task %s succeeded url=%s", task_id, public_url)
                        return AIVideoResult(
                            task_id=task_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.COMPLETED,
                            public_url=public_url,
                            duration_seconds=float(duration),
                        )
                    if status == "failed":
                        msg = data.get("task_status_msg", "Unknown error")
                        logger.warning("[Kling] Task %s failed: %s", task_id, msg)
                        return AIVideoResult(
                            task_id=task_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.FAILED,
                            error_message=msg,
                        )

                await asyncio.sleep(_POLL_INTERVAL)
                waited += _POLL_INTERVAL

        logger.warning("[Kling] Timed out polling task %s after %ds", task_id, _POLL_TIMEOUT)
        return AIVideoResult(
            task_id=task_id,
            provider=self.name,
            scene_id=scene_id,
            status=AIVideoStatus.FAILED,
            error_message=f"Timed out after {_POLL_TIMEOUT}s",
        )
