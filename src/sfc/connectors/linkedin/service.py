"""LinkedIn API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.linkedin.models import (
    LinkedInAnalytics,
    LinkedInArticle,
    LinkedInConnectorReport,
    LinkedInPost,
)

logger = logging.getLogger("sfc.connectors.linkedin")

_singleton: "LinkedInService | None" = None

_URN_COUNTER = 100_000_000


def get_linkedin_service() -> "LinkedInService":
    global _singleton
    if _singleton is None:
        _singleton = LinkedInService()
    return _singleton


class LinkedInService:
    """LinkedIn API connector. All providers mocked; inject real credentials via
    LINKEDIN_ACCESS_TOKEN / LINKEDIN_ORGANIZATION_ID env vars."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
        self._organization_id = os.environ.get("LINKEDIN_ORGANIZATION_ID", "")
        self._observability = ConnectorObservability(connector="linkedin")
        self._post_history: list[LinkedInPost] = []
        self._article_history: list[LinkedInArticle] = []
        self._urn_counter = 0

    def _next_urn(self) -> str:
        self._urn_counter += 1
        org = self._organization_id or "mock_org"
        return f"urn:li:share:{org}_{_URN_COUNTER + self._urn_counter}"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_text_post(self, text: str) -> dict[str, Any]:
        """Create a text post on the LinkedIn organization page (mocked)."""
        try:
            urn = self._next_urn()
            post = LinkedInPost(
                platform_post_id=urn,
                text=text,
                post_urn=urn,
                url=f"https://www.linkedin.com/feed/update/{urn}/",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=280.0)
            logger.info("[LinkedIn] Text post created | urn=%s", urn)
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_article(
        self, title: str, content: str, summary: str
    ) -> dict[str, Any]:
        """Create a LinkedIn article (mocked)."""
        try:
            urn = self._next_urn().replace("share", "article")
            article = LinkedInArticle(
                platform_article_id=urn,
                title=title,
                content=content,
                summary=summary,
                article_urn=urn,
                url=f"https://www.linkedin.com/pulse/{uuid4().hex[:12]}/",
                published_at=datetime.utcnow(),
            )
            self._article_history.append(article)
            self._observability.record_success(latency_ms=420.0)
            logger.info("[LinkedIn] Article created | title=%s", title[:40])
            return article.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_media_post(
        self, text: str, media_url: str, media_type: str = "image"
    ) -> dict[str, Any]:
        """Create a post with media on the LinkedIn organization page (mocked)."""
        try:
            urn = self._next_urn()
            post = LinkedInPost(
                platform_post_id=urn,
                text=text,
                media_url=media_url,
                media_type=media_type,
                post_urn=urn,
                url=f"https://www.linkedin.com/feed/update/{urn}/",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=560.0)
            logger.info("[LinkedIn] Media post created | type=%s urn=%s", media_type, urn)
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_post_analytics(self, post_urn: str) -> dict[str, Any]:
        """Get analytics for a specific post (mocked)."""
        try:
            analytics = LinkedInAnalytics(
                post_urn=post_urn,
                impressions=14_200,
                clicks=680,
                likes=420,
                comments=38,
                shares=95,
                engagement_rate=3.6,
                unique_impressions=11_800,
            )
            self._observability.record_success(latency_ms=140.0)
            return analytics.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_organization_analytics(self) -> dict[str, Any]:
        """Get organization page analytics (mocked)."""
        try:
            self._observability.record_success(latency_ms=165.0)
            return {
                "organization_id": self._organization_id or "mock_li_org",
                "followers": 28_400,
                "follower_growth_30d": 1_240,
                "impressions_30d": 420_000,
                "unique_impressions_30d": 310_000,
                "clicks_30d": 18_600,
                "engagement_rate_30d": 3.4,
                "organic_reach_30d": 285_000,
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> LinkedInConnectorReport:
        return LinkedInConnectorReport(
            posts_published=len(self._post_history),
            articles_published=len(self._article_history),
            total_impressions=len(self._post_history) * 14_200,
            total_engagement=len(self._post_history) * 551,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._organization_id)
