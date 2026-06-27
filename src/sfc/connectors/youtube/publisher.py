"""YouTube Video Publisher — bridges ClipPackage → YouTubeService upload.

Translates Video Intelligence clip packages into YouTube upload requests and
delegates to the existing YouTubeService which handles real OAuth2 + resumable
upload when credentials are present, or mock otherwise.

Credentials (set in Railway env to activate real uploads):
    YOUTUBE_CLIENT_ID
    YOUTUBE_CLIENT_SECRET
    YOUTUBE_REFRESH_TOKEN
    YOUTUBE_CHANNEL_ID
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant

logger = logging.getLogger("sfc.connectors.youtube.publisher")


class YouTubeVideoPublisher:
    """Publishes a single clip variant to YouTube."""

    def __init__(self) -> None:
        from sfc.connectors.youtube.service import get_youtube_service
        self._svc = get_youtube_service()

    async def publish(
        self,
        package: "ClipPackage",
        variant: "PlatformClipVariant",
        attribution: str = "",
    ) -> dict:
        """Upload ``variant`` to YouTube; return a result dict."""
        from sfc.connectors.youtube.models import VideoPrivacy, VideoUploadRequest

        is_short = variant.platform in ("youtube_short",)
        description = self._build_description(package, attribution)

        request = VideoUploadRequest(
            title=package.title[:100],
            description=description[:5000],
            tags=self._clean_tags(package.hashtags),
            privacy=VideoPrivacy.PUBLIC,
            file_url=variant.public_url or variant.local_path,
            thumbnail_url=variant.thumbnail_path,
            is_short=is_short,
            language="ar",
        )

        try:
            if is_short:
                result = await self._svc.upload_short(request)
            else:
                result = await self._svc.upload_video(request)

            logger.info(
                "[YouTubePublisher] clip_id=%s platform=%s video_id=%s url=%s",
                package.clip_id, variant.platform, result.video_id, result.url,
            )
            return {
                "status": "published",
                "platform": variant.platform,
                "video_id": result.video_id,
                "url": result.url,
                "is_short": is_short,
                "clip_id": package.clip_id,
            }
        except Exception as exc:
            logger.error(
                "[YouTubePublisher] Upload failed clip_id=%s: %s", package.clip_id, exc
            )
            return {
                "status": "failed",
                "platform": variant.platform,
                "error": str(exc),
                "clip_id": package.clip_id,
            }

    def _build_description(self, package: "ClipPackage", attribution: str) -> str:
        parts = [package.description or package.title]
        if attribution:
            parts.append(f"\nSource: {attribution}")
        if package.hashtags:
            parts.append("\n" + " ".join(package.hashtags))
        return "\n".join(parts)

    def _clean_tags(self, hashtags: list[str]) -> list[str]:
        return [h.lstrip("#") for h in hashtags][:500]
