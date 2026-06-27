"""Instagram Reels Publisher — real Content Publishing API implementation.

Uses the Instagram Graph API v20.0 two-step publishing flow:
  1. POST /{ig_user_id}/media     → creates a media container (returns creation_id)
  2. GET  /{ig_user_id}/media?fields=status_code  → poll until FINISHED
  3. POST /{ig_user_id}/media_publish → publishes the container

IMPORTANT: Instagram requires a **publicly accessible URL** for video ingestion.
If ``variant.local_path`` is set but no public URL is available, this publisher
logs a warning and skips the upload rather than failing the pipeline.

Credentials (set in Railway env to activate real uploads):
    INSTAGRAM_ACCESS_TOKEN          — user access token with instagram_basic +
                                      instagram_content_publish scopes
    INSTAGRAM_BUSINESS_ACCOUNT_ID  — numeric Instagram Business Account ID

Config:
    INSTAGRAM_PUBLISH_TIMEOUT_SECS — polling timeout (default: 300)
    INSTAGRAM_POLL_INTERVAL_SECS   — polling interval (default: 5)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant

logger = logging.getLogger("sfc.connectors.instagram.publisher")

_GRAPH_API_BASE = "https://graph.facebook.com/v20.0"
_DEFAULT_POLL_TIMEOUT = 300
_DEFAULT_POLL_INTERVAL = 5


class InstagramReelPublisher:
    """Publishes a Reel to Instagram via Graph API Content Publishing."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self._ig_user_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
        self._poll_timeout = int(
            os.environ.get("INSTAGRAM_PUBLISH_TIMEOUT_SECS", str(_DEFAULT_POLL_TIMEOUT))
        )
        self._poll_interval = int(
            os.environ.get("INSTAGRAM_POLL_INTERVAL_SECS", str(_DEFAULT_POLL_INTERVAL))
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._access_token and self._ig_user_id)

    async def publish(
        self,
        package: "ClipPackage",
        variant: "PlatformClipVariant",
        public_video_url: str = "",
        attribution: str = "",
    ) -> dict:
        """Publish a Reel. Uses ``variant.public_url`` if ``public_video_url`` not supplied."""
        # Prefer the URL passed explicitly, fall back to the variant's own public_url
        public_video_url = public_video_url or getattr(variant, "public_url", "")

        if not self.is_configured:
            logger.warning(
                "[InstagramPublisher] Credentials not set — skipping clip_id=%s",
                package.clip_id,
            )
            return {
                "status": "skipped",
                "reason": "INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID not set",
                "platform": variant.platform,
                "clip_id": package.clip_id,
            }

        if not public_video_url:
            logger.warning(
                "[InstagramPublisher] No public video URL for clip_id=%s — "
                "Instagram requires a publicly accessible URL; skipping",
                package.clip_id,
            )
            return {
                "status": "skipped",
                "reason": "No public_video_url; Instagram cannot download from local paths",
                "platform": variant.platform,
                "clip_id": package.clip_id,
            }

        caption = self._build_caption(package, attribution)

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Create media container
                container_id = await self._create_container(
                    client, public_video_url, caption
                )
                if not container_id:
                    return {
                        "status": "failed",
                        "reason": "Failed to create media container",
                        "clip_id": package.clip_id,
                    }

                # Step 2: Poll until container status = FINISHED
                ready = await self._wait_for_container(client, container_id)
                if not ready:
                    return {
                        "status": "failed",
                        "reason": f"Container {container_id} did not reach FINISHED state",
                        "clip_id": package.clip_id,
                    }

                # Step 3: Publish the container
                media_id = await self._publish_container(client, container_id)
                if not media_id:
                    return {
                        "status": "failed",
                        "reason": "media_publish returned no media_id",
                        "clip_id": package.clip_id,
                    }

            permalink = (
                f"https://www.instagram.com/reel/{media_id}/"
            )
            logger.info(
                "[InstagramPublisher] Published clip_id=%s media_id=%s",
                package.clip_id, media_id,
            )
            return {
                "status": "published",
                "platform": "instagram_reel",
                "media_id": media_id,
                "permalink": permalink,
                "clip_id": package.clip_id,
            }

        except Exception as exc:
            logger.error(
                "[InstagramPublisher] Publish failed clip_id=%s: %s",
                package.clip_id, exc,
            )
            return {
                "status": "failed",
                "error": str(exc),
                "clip_id": package.clip_id,
            }

    async def _create_container(
        self, client: "httpx.AsyncClient", video_url: str, caption: str
    ) -> str:
        """Step 1: POST to /{ig_user_id}/media to create a Reels container."""
        resp = await client.post(
            f"{_GRAPH_API_BASE}/{self._ig_user_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption[:2200],
                "access_token": self._access_token,
            },
        )
        if resp.status_code != 200:
            logger.warning(
                "[InstagramPublisher] Container creation HTTP %d: %s",
                resp.status_code, resp.text[:300],
            )
            return ""
        return resp.json().get("id", "")

    async def _wait_for_container(
        self, client: "httpx.AsyncClient", container_id: str
    ) -> bool:
        """Step 2: Poll status until FINISHED or timeout."""
        waited = 0
        while waited < self._poll_timeout:
            resp = await client.get(
                f"{_GRAPH_API_BASE}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": self._access_token,
                },
            )
            if resp.status_code == 200:
                status = resp.json().get("status_code", "")
                if status == "FINISHED":
                    return True
                if status == "ERROR":
                    logger.warning(
                        "[InstagramPublisher] Container %s entered ERROR state", container_id
                    )
                    return False
            await asyncio.sleep(self._poll_interval)
            waited += self._poll_interval

        logger.warning(
            "[InstagramPublisher] Timed out waiting for container %s after %ds",
            container_id, self._poll_timeout,
        )
        return False

    async def _publish_container(
        self, client: "httpx.AsyncClient", container_id: str
    ) -> str:
        """Step 3: POST to /{ig_user_id}/media_publish."""
        resp = await client.post(
            f"{_GRAPH_API_BASE}/{self._ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self._access_token,
            },
        )
        if resp.status_code != 200:
            logger.warning(
                "[InstagramPublisher] media_publish HTTP %d: %s",
                resp.status_code, resp.text[:300],
            )
            return ""
        return resp.json().get("id", "")

    def _build_caption(self, package: "ClipPackage", attribution: str) -> str:
        parts = [package.description or package.title]
        if attribution:
            parts.append(f"\n📹 {attribution}")
        if package.hashtags:
            parts.append("\n" + " ".join(package.hashtags))
        return "\n".join(parts)
