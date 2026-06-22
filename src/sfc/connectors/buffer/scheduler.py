"""Buffer post scheduling — optimal time selection and queue management."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from sfc.connectors.buffer.models import BufferPlatform, BufferPost, BufferPostStatus

logger = logging.getLogger("sfc.connectors.buffer.scheduler")

# Default publishing windows (hours, UTC) per platform — Saudi Football audience
_DEFAULT_WINDOWS: dict[str, list[int]] = {
    "x": [7, 12, 18, 21],          # morning, noon, post-match, evening
    "youtube": [16, 19],            # after-school / prime time
    "instagram": [8, 12, 19],
    "tiktok": [7, 13, 20],
    "facebook": [9, 12, 18],
    "threads": [9, 12, 18],
    "linkedin": [9, 12, 17],
}


class BufferScheduler:
    """Calculates optimal publish times and builds schedule queues."""

    def __init__(self) -> None:
        self._tz_offset_hours = int(os.environ.get("PUBLISH_TZ_OFFSET_HOURS", "3"))  # AST=UTC+3

    def next_slot(
        self,
        platform: str,
        *,
        after: datetime | None = None,
        min_spacing_minutes: int = 30,
    ) -> datetime:
        """Return the next optimal publish slot for the given platform."""
        now = after or datetime.utcnow()
        windows = _DEFAULT_WINDOWS.get(platform, [12, 18])

        for day_offset in range(7):
            for hour in windows:
                slot = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
                    days=day_offset, hours=hour
                )
                gap = (slot - now).total_seconds() / 60
                if gap >= min_spacing_minutes:
                    return slot

        # Fallback: 1 hour from now
        return now + timedelta(hours=1)

    def schedule_posts(
        self,
        posts: list[BufferPost],
        *,
        stagger_minutes: int = 15,
        start_after: datetime | None = None,
    ) -> list[BufferPost]:
        """Assign scheduled_at times to posts, staggering them to avoid bunching."""
        cursor = start_after or datetime.utcnow()
        for post in posts:
            slot = self.next_slot(post.platform.value, after=cursor, min_spacing_minutes=stagger_minutes)
            post.scheduled_at = slot
            post.status = BufferPostStatus.SCHEDULED
            cursor = slot + timedelta(minutes=stagger_minutes)
        return posts

    def build_campaign_schedule(
        self,
        content_items: list[dict[str, Any]],
        platforms: list[str],
    ) -> list[dict[str, Any]]:
        """Build a publishing schedule for a campaign across platforms.

        Each item in content_items should have: content, media_url, hashtags.
        Returns enriched items with scheduled_at and platform.
        """
        schedule: list[dict[str, Any]] = []
        cursors: dict[str, datetime] = {}

        for item in content_items:
            for platform in platforms:
                after = cursors.get(platform, datetime.utcnow())
                slot = self.next_slot(platform, after=after)
                cursors[platform] = slot + timedelta(minutes=15)
                schedule.append({
                    **item,
                    "platform": platform,
                    "scheduled_at": slot.isoformat(),
                })

        return schedule


_singleton: BufferScheduler | None = None


def get_buffer_scheduler() -> BufferScheduler:
    global _singleton
    if _singleton is None:
        _singleton = BufferScheduler()
    return _singleton
