"""WordPress REST API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.wordpress.models import (
    WordPressConnectorReport,
    WordPressMedia,
    WordPressPost,
    WordPressPostStatus,
)

logger = logging.getLogger("sfc.connectors.wordpress")

_singleton: "WordPressService | None" = None

_POST_ID_COUNTER = 10_000


def get_wordpress_service() -> "WordPressService":
    global _singleton
    if _singleton is None:
        _singleton = WordPressService()
    return _singleton


class WordPressService:
    """WordPress REST API connector. All providers mocked; inject real credentials via
    WORDPRESS_SITE_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD env vars."""

    def __init__(self) -> None:
        self._site_url = os.environ.get("WORDPRESS_SITE_URL", "")
        self._username = os.environ.get("WORDPRESS_USERNAME", "")
        self._app_password = os.environ.get("WORDPRESS_APP_PASSWORD", "")
        self._observability = ConnectorObservability(connector="wordpress")
        self._post_history: list[WordPressPost] = []
        self._media_history: list[WordPressMedia] = []
        self._post_counter = 0
        self._media_counter = 0

    def _next_post_id(self) -> int:
        self._post_counter += 1
        return _POST_ID_COUNTER + self._post_counter

    def _next_media_id(self) -> int:
        self._media_counter += 1
        return _POST_ID_COUNTER + 5_000 + self._media_counter

    def _base_url(self) -> str:
        return self._site_url or "https://sfc-football.com"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_post(
        self,
        title: str,
        content: str,
        excerpt: str = "",
        tags: list[str] | None = None,
        categories: list[str] | None = None,
        status: str = "publish",
    ) -> dict[str, Any]:
        """Create a WordPress post via REST API (mocked)."""
        try:
            post_id = self._next_post_id()
            slug = title.lower().replace(" ", "-")[:60]
            wp_status = WordPressPostStatus(status) if status in WordPressPostStatus._value2member_map_ else WordPressPostStatus.PUBLISH
            post = WordPressPost(
                platform_post_id=post_id,
                title=title,
                content=content,
                excerpt=excerpt,
                tags=tags or [],
                categories=categories or ["Football", "Saudi Pro League"],
                status=wp_status,
                slug=slug,
                url=f"{self._base_url()}/{slug}-{post_id}/",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=460.0)
            logger.info("[WordPress] Post created | id=%d title=%s", post_id, title[:40])
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def upload_media(
        self, file_url: str, filename: str, alt_text: str = ""
    ) -> dict[str, Any]:
        """Upload media to WordPress Media Library (mocked)."""
        try:
            media_id = self._next_media_id()
            media = WordPressMedia(
                platform_media_id=media_id,
                filename=filename,
                file_url=file_url,
                alt_text=alt_text,
                source_url=f"{self._base_url()}/wp-content/uploads/{uuid4().hex[:8]}/{filename}",
                uploaded_at=datetime.utcnow(),
            )
            self._media_history.append(media)
            self._observability.record_success(latency_ms=620.0)
            logger.info("[WordPress] Media uploaded | id=%d file=%s", media_id, filename)
            return media.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_post_analytics(self, post_id: int) -> dict[str, Any]:
        """Get analytics for a WordPress post (mocked via Jetpack/Matomo)."""
        try:
            self._observability.record_success(latency_ms=140.0)
            return {
                "post_id": post_id,
                "views": 4_800,
                "unique_visitors": 3_200,
                "avg_time_on_page_seconds": 142,
                "bounce_rate": 0.38,
                "social_shares": 240,
                "comments": 18,
                "fetched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> WordPressConnectorReport:
        return WordPressConnectorReport(
            posts_published=len(self._post_history),
            media_uploaded=len(self._media_history),
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._site_url and self._username and self._app_password)
