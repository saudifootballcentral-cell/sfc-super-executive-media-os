"""X (Twitter) API connector service — real API when credentials present, mock otherwise."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse
import uuid
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

_POST_ID_COUNTER = 100_000_000_000_000_000
_MEDIA_ID_COUNTER = 100_000_000_000_000
_SCHED_ID_COUNTER = 1_000_000_000_000


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
        self._post_counter = 0
        self._media_counter = 0
        self._sched_counter = 0
        self._monitor_config = XMonitorConfig(
            keywords=["السعودي", "الدوري", "SFC", "SPL"],
            hashtags=["#الدوري_السعودي", "#SaudiFootball", "#SPL"],
            accounts=["@SFCMedia", "@SaudiProLeague"],
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def _is_live(self) -> bool:
        return all([self._api_key, self._api_secret, self._access_token, self._access_secret])

    def _oauth1_header(self, method: str, url: str) -> str:
        """Build OAuth 1.0a HMAC-SHA1 Authorization header for X API v2."""
        oauth_params: dict[str, str] = {
            "oauth_consumer_key": self._api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self._access_token,
            "oauth_version": "1.0",
        }
        param_string = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted(oauth_params.items())
        )
        base_string = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe=""),
        ])
        signing_key = (
            f"{urllib.parse.quote(self._api_secret, safe='')}"
            f"&{urllib.parse.quote(self._access_secret, safe='')}"
        )
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        oauth_params["oauth_signature"] = signature
        header_parts = ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        return f"OAuth {header_parts}"

    async def _real_create_post(
        self, text: str, media_ids: list[str] | None = None, reply_to_id: str = ""
    ) -> XPost:
        """Real X API v2 POST /2/tweets call."""
        import httpx

        url = "https://api.twitter.com/2/tweets"
        body: dict[str, Any] = {"text": text}
        if reply_to_id:
            body["reply"] = {"in_reply_to_tweet_id": reply_to_id}
        if media_ids:
            body["media"] = {"media_ids": media_ids}

        headers = {
            "Authorization": self._oauth1_header("POST", url),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

        tweet_id = data["data"]["id"]
        post = XPost(
            text=text,
            media_ids=media_ids or [],
            platform_post_id=tweet_id,
            status=XPostStatus.PUBLISHED,
            published_at=datetime.utcnow(),
            url=f"https://x.com/i/web/status/{tweet_id}",
            reply_to_id=reply_to_id,
        )
        self._post_history.append(post)
        self._observability.record_success(latency_ms=0.0)
        logger.info("[X] LIVE post published | id=%s chars=%d", tweet_id, len(text))
        return post

    async def create_post(
        self,
        text: str,
        media_ids: list[str] | None = None,
        reply_to_id: str = "",
    ) -> XPost:
        try:
            self._validate_text(text)
            if self._is_live():
                return await self._real_create_post(text, media_ids, reply_to_id)
            self._post_counter += 1
            platform_id = f"x_{_POST_ID_COUNTER + self._post_counter}"
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
            self._observability.record_success(latency_ms=220.0)
            logger.info("[X] Mock post | id=%s chars=%d", platform_id, len(text))
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
            self._media_counter += 1
            media = XMedia(
                platform_media_id=f"media_{_MEDIA_ID_COUNTER + self._media_counter}",
                media_type=media_type,
                file_url=file_url,
                alt_text=alt_text,
            )
            self._observability.record_success(latency_ms=580.0)
            logger.info("[X] Media uploaded | type=%s", media_type.value)
            return media
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return XMedia(file_url=file_url)

    async def schedule_post(self, text: str, scheduled_at: datetime) -> XPost:
        try:
            self._validate_text(text)
            self._sched_counter += 1
            post = XPost(
                text=text,
                status=XPostStatus.SCHEDULED,
                scheduled_at=scheduled_at,
                platform_post_id=f"sched_{_SCHED_ID_COUNTER + self._sched_counter}",
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=130.0)
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
            from sfc.data.fixtures.loader import get_fixture_loader
            loader = get_fixture_loader()
            data = loader.get_x_post_metrics("default")

            metrics = XMetrics(
                post_id=post_id,
                platform_post_id=post_id,
                views=int(data.get("views", 28000)),
                likes=int(data.get("likes", 840)),
                retweets=int(data.get("retweets", 280)),
                quote_tweets=int(data.get("quote_tweets", 52)),
                replies=int(data.get("replies", 98)),
                bookmarks=int(data.get("bookmarks", 180)),
                impressions=int(data.get("impressions", 72000)),
                profile_visits=int(data.get("profile_visits", 420)),
                link_clicks=int(data.get("link_clicks", 240)),
                engagement_rate=float(data.get("engagement_rate", 3.8)),
            )
            self._observability.record_success(latency_ms=140.0)
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
                        participant_count=50 + i * 120,
                        total_impressions=8000 + i * 15000,
                        sentiment=sentiments[i % len(sentiments)],
                        posts=[
                            {"text": f"Mock post about {query} #{i}", "author": f"@user_{i}"}
                        ],
                    )
                )
            self._observability.record_success(latency_ms=175.0)
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
            from sfc.data.fixtures.loader import get_fixture_loader
            loader = get_fixture_loader()
            fixture_trends = {t["term"]: t for t in loader.get_trends()}

            trends: list[XTrend] = []
            for term in terms:
                fixture = fixture_trends.get(term, {})
                volume = int(fixture.get("tweet_volume", 10000))
                velocity = float(fixture.get("velocity", 2.5))
                sentiment = str(fixture.get("sentiment", "neutral"))
                relevance = float(fixture.get("relevance_score", 75.0))

                trends.append(
                    XTrend(
                        term=term,
                        tweet_volume=volume,
                        trend_type=trend_type,
                        velocity=velocity,
                        sentiment=sentiment,
                        relevance_score=relevance,
                    )
                )
            self._observability.record_success(latency_ms=140.0)
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
