"""Medium API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.medium.models import (
    MediumConnectorReport,
    MediumPost,
    MediumPublishStatus,
)

logger = logging.getLogger("sfc.connectors.medium")

_singleton: "MediumService | None" = None

_MOCK_PUBLICATION_ID = "pub_sfc_football_mock"


def get_medium_service() -> "MediumService":
    global _singleton
    if _singleton is None:
        _singleton = MediumService()
    return _singleton


class MediumService:
    """Medium API connector. All providers mocked; inject real credentials via
    MEDIUM_ACCESS_TOKEN / MEDIUM_AUTHOR_ID env vars."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("MEDIUM_ACCESS_TOKEN", "")
        self._author_id = os.environ.get("MEDIUM_AUTHOR_ID", "")
        self._observability = ConnectorObservability(connector="medium")
        self._post_history: list[MediumPost] = []
        self._post_counter = 0

    def _next_post_id(self) -> str:
        self._post_counter += 1
        return f"medium_{uuid4().hex[:12]}_{self._post_counter}"

    def _make_slug(self, title: str) -> str:
        return title.lower().replace(" ", "-")[:50]

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_post(
        self,
        title: str,
        content_html: str,
        tags: list[str],
        publish_status: str = "public",
    ) -> dict[str, Any]:
        """Create a post on Medium (mocked)."""
        try:
            post_id = self._next_post_id()
            slug = self._make_slug(title)
            status = MediumPublishStatus(publish_status) if publish_status in MediumPublishStatus._value2member_map_ else MediumPublishStatus.PUBLIC
            post = MediumPost(
                platform_post_id=post_id,
                title=title,
                content_html=content_html,
                tags=tags[:5],  # Medium supports up to 5 tags
                publish_status=status,
                url=f"https://medium.com/@sfc_football/{slug}-{post_id[-8:]}",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=380.0)
            logger.info("[Medium] Post created | id=%s title=%s", post_id, title[:40])
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def get_publication_id(self) -> str:
        """Get the publication ID for the SFC publication on Medium (mocked)."""
        try:
            self._observability.record_success(latency_ms=100.0)
            return _MOCK_PUBLICATION_ID
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return ""

    async def create_publication_post(
        self,
        publication_id: str,
        title: str,
        content_html: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """Create a post under a Medium publication (mocked)."""
        try:
            post_id = self._next_post_id()
            slug = self._make_slug(title)
            post = MediumPost(
                platform_post_id=post_id,
                title=title,
                content_html=content_html,
                tags=tags[:5],
                publish_status=MediumPublishStatus.PUBLIC,
                publication_id=publication_id,
                url=f"https://medium.com/sfc-football/{slug}-{post_id[-8:]}",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=420.0)
            logger.info(
                "[Medium] Publication post created | pub=%s id=%s",
                publication_id, post_id,
            )
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> MediumConnectorReport:
        pub_posts = sum(1 for p in self._post_history if p.publication_id)
        return MediumConnectorReport(
            posts_published=len(self._post_history),
            publication_posts=pub_posts,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._author_id)
