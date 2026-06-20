"""Publishing Division — distributes approved content to all platforms."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from core.models import ContentItem, ContentStatus, Division, Platform, SFCEvent
from divisions.base import BaseDivision

PLATFORM_ADAPTERS: dict[Platform, dict[str, Any]] = {
    Platform.TIKTOK: {"max_chars": 150, "hashtag_limit": 5, "supports_video": True},
    Platform.INSTAGRAM_REELS: {"max_chars": 2200, "hashtag_limit": 30, "supports_video": True},
    Platform.INSTAGRAM_STORIES: {"max_chars": 200, "duration_s": 15, "supports_video": True},
    Platform.INSTAGRAM_FEED: {"max_chars": 2200, "hashtag_limit": 30, "supports_video": False},
    Platform.YOUTUBE_SHORTS: {"max_chars": 500, "supports_video": True},
    Platform.YOUTUBE: {"max_chars": 5000, "supports_video": True},
    Platform.X: {"max_chars": 280, "supports_video": True},
    Platform.TELEGRAM: {"max_chars": 4096, "supports_video": True},
    Platform.WHATSAPP: {"max_chars": 1024, "supports_video": True},
    Platform.WEBSITE: {"max_chars": 100000, "supports_video": False},
    Platform.NEWSLETTER: {"max_chars": 50000, "supports_video": False},
}


class PublishingDivision(BaseDivision):
    """Handles multi-platform content distribution.

    Publishing gate enforced: content must be APPROVED before publishing.
    """

    division = Division.PUBLISHING

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        return None

    def publish(self, content: ContentItem) -> dict[str, Any]:
        if not content.is_publishable:
            self.logger.warning(
                "[Publishing] BLOCKED — content %s is not publishable (status=%s)",
                content.content_id,
                content.status,
            )
            return {
                "published": False,
                "reason": f"Content not publishable. Status: {content.status}",
                "content_id": str(content.content_id),
            }

        results: dict[str, Any] = {}
        for platform in content.platforms:
            result = self._publish_to_platform(content, Platform(platform))
            results[platform if isinstance(platform, str) else platform.value] = result

        content.status = ContentStatus.PUBLISHED
        content.published_at = datetime.utcnow()

        publish_record = {
            "content_id": str(content.content_id),
            "published_at": content.published_at.isoformat(),
            "platforms": results,
        }
        self.memory.set(f"published:{content.content_id}", publish_record)
        self.logger.info("[Publishing] Published %s to %d platforms", content.content_id, len(results))

        return {"published": True, "content_id": str(content.content_id), "results": results}

    def _publish_to_platform(self, content: ContentItem, platform: Platform) -> dict[str, Any]:
        adapter = PLATFORM_ADAPTERS.get(platform, {})
        max_chars = adapter.get("max_chars", 280)
        body_preview = content.body[:max_chars] if content.body else ""

        self.logger.info("[Publishing] → %s: %s", platform.value, content.title[:60])

        return {
            "status": "queued",
            "platform": platform.value,
            "char_count": len(body_preview),
            "max_chars": max_chars,
            "publish_id": str(uuid4()),
        }

    def get_publish_log(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("published:")
        ]
