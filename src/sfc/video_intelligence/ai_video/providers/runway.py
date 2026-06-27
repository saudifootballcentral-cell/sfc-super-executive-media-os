"""Runway ML video provider.

API: https://api.dev.runwayml.com/v1/image_to_video
Auth: Bearer RUNWAYML_API_SECRET
Header: X-Runway-Version: 2024-11-06
Flow: POST → task id → poll GET /v1/tasks/{id} until status == SUCCEEDED
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.ai_video.providers.base import AIVideoProvider

logger = logging.getLogger("sfc.connectors.ai_video.runway")

_BASE = "https://api.dev.runwayml.com/v1"
_POLL_INTERVAL = 10
_POLL_TIMEOUT = 300


class RunwayVideoProvider(AIVideoProvider):
    """Runway ML text/image-to-video."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("RUNWAYML_API_SECRET", "")

    @property
    def name(self) -> str:
        return "runway"

    @property
    def is_enabled(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        }

    async def generate(self, scene) -> AIVideoResult:
        if not self.is_enabled:
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.SKIPPED,
                error_message="RUNWAYML_API_SECRET not set",
            )

        try:
            import httpx

            ratio = "1280:768" if scene.aspect_ratio == "16:9" else "768:1280"
            duration = 5 if scene.duration_seconds <= 5 else 10

            payload: dict = {
                "promptText": scene.visual_prompt,
                "ratio": ratio,
                "duration": duration,
            }
            if scene.reference_image_url:
                payload["promptImage"] = scene.reference_image_url

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{_BASE}/image_to_video",
                    headers=self._headers(),
                    json=payload,
                )

            if resp.status_code not in (200, 201):
                logger.warning("[Runway] Create task HTTP %d: %s", resp.status_code, resp.text[:200])
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            task_id = data.get("id", "")
            if not task_id:
                return AIVideoResult(
                    task_id=str(uuid4()),
                    provider=self.name,
                    scene_id=scene.scene_id,
                    status=AIVideoStatus.FAILED,
                    error_message="No task id in response",
                )

            return await self._poll(task_id, scene.scene_id, duration)

        except Exception as exc:
            logger.error("[Runway] generate failed scene=%s: %s", scene.scene_id, exc)
            return AIVideoResult(
                task_id=str(uuid4()),
                provider=self.name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.FAILED,
                error_message=str(exc),
            )

    async def _poll(self, task_id: str, scene_id: str, duration: int) -> AIVideoResult:
        import httpx

        waited = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            while waited < _POLL_TIMEOUT:
                resp = await client.get(
                    f"{_BASE}/tasks/{task_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")
                    if status == "SUCCEEDED":
                        outputs = data.get("output", [])
                        public_url = outputs[0] if outputs else ""
                        logger.info("[Runway] Task %s succeeded url=%s", task_id, public_url)
                        return AIVideoResult(
                            task_id=task_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.COMPLETED,
                            public_url=public_url,
                            duration_seconds=float(duration),
                        )
                    if status == "FAILED":
                        msg = data.get("failure", "Unknown error")
                        logger.warning("[Runway] Task %s failed: %s", task_id, msg)
                        return AIVideoResult(
                            task_id=task_id,
                            provider=self.name,
                            scene_id=scene_id,
                            status=AIVideoStatus.FAILED,
                            error_message=msg,
                        )

                await asyncio.sleep(_POLL_INTERVAL)
                waited += _POLL_INTERVAL

        logger.warning("[Runway] Timed out polling task %s after %ds", task_id, _POLL_TIMEOUT)
        return AIVideoResult(
            task_id=task_id,
            provider=self.name,
            scene_id=scene_id,
            status=AIVideoStatus.FAILED,
            error_message=f"Timed out after {_POLL_TIMEOUT}s",
        )
