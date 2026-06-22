"""X (Twitter) API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Any

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.x.models import (
    XConnectorReport,
    XConversation,
    XMedia,
    XMediaType,
    XMetrics,
    XMonitorConfig,
    XPost,
    XPostStatus,
    XThread,
    XTrend,
)

logger = logging.getLogger("sfc.connectors.x")

_singleton: "XService | None" = None


def get_x_service() -> "XService":
    global _singleton
    if _singleton is None:
        _singleton = XService()
    return _singleton


class XService:
    """X API v2 connector. All providers mocked; inject real credentials via
    X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET env vars."""

    _SAUDI_TRENDS = [
        "#الدوري_السعودي", "#SaudiProLeague", "#AlHilal", "#AlNassr",
        "#WorldCup2034", "#SaudiFootball", "#SPL", "#كرة_القدم",
    ]

    def __init__(self) -> None:
        self._api_key = os.environ.get("X_API_KEY", "")
        self._api_secret = os.environ.get("X_API_SECRET", "")
        self._access_token = os.environ.get("X_ACCESS_TOKEN", "")
        self._access_secret = os.environ.get("X_ACCESS_SECRET", "")
        self._observability = ConnectorObservability(connector="x")
        self._post_history: list[XPost] = []
        self._thread_history: list[XThread] = []
        self._monitor_config = XMonitorConfig(
            keywords=["السعودي", "الدوري", "SFC", "SPL"],
            hashtags=["#الدوري_السعودي", "#SaudiFootball", "#SPL"],
            accounts=["@SFCMedia", "@SaudiProLeague"],
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_post(
        self,
        text: str,
        media_ids: list[str] | None = None,
        reply_to_id: str = "",
    ) -> XPost:
        try:
            self._validate_text(text)
            platform_id = f"x_{random.randint(10**17, 10**18)}"
            post = XPost(
                text=text,
                media_ids=media_ids or [],
                platform_post_id=platform_id,
                status=XPostStatus.PUBLISHED,
                published_at=datetime.utcnow(),
                url=f"https://x.com/SFCMedia/status/{platform_id}",
                reply_to_id=reply_to_id,
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=random.uniform(100, 400))
            logger.info("[X] Post published | id=%s chars=%d", platform_id, len(text))
            return post
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return XPost(text=text, status=XPostStatus.FAILED, error_message=str(exc))

    async def create_thread(
        self, texts: list[str], topic: str = "", media_ids: list[str] | None = None
    ) -> XThread:
        try:
            posts: list[XPost] = []
            previous_id = ""
            for i, text in enumerate(texts):
                media = [media_ids[i]] if media_ids and i < len(media_ids) else []
                post = await self.create_post(text, media_ids=media, reply_to_id=previous_id)
                posts.append(post)
                previous_id = post.platform_post_id
                if i < len(texts) - 1:
                    await asyncio.sleep(0)

            thread = XThread(
                posts=posts,
                topic=topic or texts[0][:40],
                total_posts=len(posts),
                published_at=datetime.utcnow(),
                status=XPostStatus.PUBLISHED,
                platform_thread_root_id=posts[0].platform_post_id if posts else "",
            )
            self._thread_history.append(thread)
            logger.info("[X] Thread published | posts=%d topic=%s", len(posts), topic[:30])
            return thread
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return XThread(topic=topic, status=XPostStatus.FAILED)

    async def upload_media(
        self, file_url: str, media_type: XMediaType = XMediaType.IMAGE, alt_text: str = ""
    ) -> XMedia:
        try:
            media = XMedia(
                platform_media_id=f"media_{random.randint(10**14, 10**15)}",
                media_type=media_type,
                file_url=file_url,
                alt_text=alt_text,
            )
            self._observability.record_success(latency_ms=random.uniform(200, 1000))
            logger.info("[X] Media uploaded | type=%s", media_type.value)
            return media
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return XMedia(file_url=file_url)

    async def schedule_post(self, text: str, scheduled_at: datetime) -> XPost:
        try:
            self._validate_text(text)
            post = XPost(
                text=text,
                status=XPostStatus.SCHEDULED,
                scheduled_at=scheduled_at,
                platform_post_id=f"sched_{random.randint(10**12, 10**13)}",
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=random.uniform(80, 200))
            logger.info("[X] Post scheduled | at=%s", scheduled_at.isoformat())
            return post
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return XPost(text=text, status=XPostStatus.FAILED, error_message=str(exc))

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_metrics(self, post_id: str) -> XMetrics:
        try:
            metrics = XMetrics(
                post_id=post_id,
                platform_post_id=post_id,
                views=random.randint(500, 500_000),
                likes=random.randint(10, 10_000),
                retweets=random.randint(5, 2_000),
                quote_tweets=random.randint(1, 500),
                replies=random.randint(2, 1_000),
                bookmarks=random.randint(5, 5_000),
                impressions=random.randint(1_000, 1_000_000),
                profile_visits=random.randint(50, 5_000),
                link_clicks=random.randint(10, 2_000),
                engagement_rate=round(random.uniform(1.5, 12.0), 2),
            )
            self._observability.record_success(latency_ms=random.uniform(80, 200))
            return metrics
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return XMetrics(post_id=post_id)

    # ------------------------------------------------------------------
    # Social Intelligence
    # ------------------------------------------------------------------

    async def search_conversations(
        self, query: str, max_results: int = 10
    ) -> list[XConversation]:
        try:
            conversations: list[XConversation] = []
            sentiments = ["positive", "neutral", "positive", "excited", "neutral"]
            for i in range(min(max_results, 3)):
                conversations.append(
                    XConversation(
                        topic=f"{query} conversation {i+1}",
                        keyword=query,
                        participant_count=random.randint(5, 500),
                        total_impressions=random.randint(1_000, 100_000),
                        sentiment=sentiments[i % len(sentiments)],
                        posts=[
                            {"text": f"Mock post about {query} #{i}", "author": f"@user_{i}"}
                        ],
                    )
                )
            self._observability.record_success(latency_ms=random.uniform(100, 300))
            return conversations
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    async def monitor_keywords(
        self, keywords: list[str] | None = None
    ) -> list[XTrend]:
        keywords = keywords or self._monitor_config.keywords
        return await self._fetch_trends(keywords, trend_type="keyword")

    async def monitor_hashtags(
        self, hashtags: list[str] | None = None
    ) -> list[XTrend]:
        hashtags = hashtags or self._monitor_config.hashtags
        return await self._fetch_trends(hashtags, trend_type="hashtag")

    async def get_trending_topics(self, location: str = "Saudi Arabia") -> list[XTrend]:
        return await self._fetch_trends(self._SAUDI_TRENDS, trend_type="trending")

    async def _fetch_trends(
        self, terms: list[str], trend_type: str = "hashtag"
    ) -> list[XTrend]:
        try:
            trends: list[XTrend] = []
            for term in terms:
                volume = random.randint(500, 500_000)
                trends.append(
                    XTrend(
                        term=term,
                        tweet_volume=volume,
                        trend_type=trend_type,
                        velocity=round(random.uniform(0.5, 10.0), 2),
                        sentiment=random.choice(["positive", "neutral", "excited"]),
                        relevance_score=round(random.uniform(60, 99), 1),
                    )
                )
            self._observability.record_success(latency_ms=random.uniform(80, 200))
            return sorted(trends, key=lambda t: t.tweet_volume, reverse=True)
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    async def update_monitor_config(self, config: XMonitorConfig) -> None:
        self._monitor_config = config

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> XConnectorReport:
        trends = await self.get_trending_topics()
        conversations = await self.search_conversations("SaudiFootball", max_results=3)
        return XConnectorReport(
            posts_published=len([p for p in self._post_history if p.status == XPostStatus.PUBLISHED]),
            threads_published=len(self._thread_history),
            trends_detected=len(trends),
            conversations_detected=len(conversations),
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    def _validate_text(self, text: str) -> None:
        if len(text) > 280:
            raise ValueError(f"X post text exceeds 280 characters ({len(text)})")

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._api_key and self._api_secret)
