"""Buffer real publisher — creates and tracks posts via the Buffer API.

LIVE_PUBLISHING_ENABLED=true  → real HTTP calls to Buffer API
LIVE_PUBLISHING_ENABLED=false → dry-run, no network calls made
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.connectors.buffer.api_client import BufferAPIClient, BufferAPIError, get_buffer_api_client
from sfc.connectors.buffer.models import BufferPost, BufferPostStatus, BufferPublishResult
from sfc.connectors.buffer.rate_limits import BufferRateLimiter, get_buffer_rate_limiter
from sfc.connectors.buffer.retry_manager import BufferRetryManager, get_buffer_retry_manager

logger = logging.getLogger("sfc.connectors.buffer.publisher")


class MediaValidationError(Exception):
    """Raised when media file fails pre-publish validation."""


class PublishApprovalError(Exception):
    """Raised when the triple-lock approval gate blocks publishing."""


class BufferPublisher:
    """Real publishing engine for Buffer.

    Triple-lock approval gate:
      1. governance_approved must be True
      2. operator_approved must be True
      3. LIVE_PUBLISHING_ENABLED=true

    If any lock is open, publishing is blocked (dry-run or hard error).

    Never returns SUCCESS unless Buffer confirms post creation with a real ID.
    """

    def __init__(
        self,
        client: BufferAPIClient | None = None,
        rate_limiter: BufferRateLimiter | None = None,
        retry_manager: BufferRetryManager | None = None,
    ) -> None:
        self._client = client or get_buffer_api_client()
        self._rate_limiter = rate_limiter or get_buffer_rate_limiter()
        self._retry = retry_manager or get_buffer_retry_manager()
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def create_post(
        self,
        post: BufferPost,
        profile_id: str,
        *,
        governance_approved: bool,
        operator_approved: bool,
        rights_status: str = "owned",
    ) -> BufferPublishResult:
        """Create a Buffer post after passing the triple-lock gate.

        Returns a BufferPublishResult with a confirmed Buffer post ID on success.
        Raises PublishApprovalError if gate blocks publishing.
        """
        self._triple_lock_check(post, governance_approved, operator_approved, rights_status)

        if post.media_url:
            self._validate_media(post.media_url)

        if not self._live:
            return self._dry_run_result(post)

        await self._rate_limiter.acquire()

        async def _attempt() -> BufferPublishResult:
            return await self._call_create_update(post, profile_id)

        return await self._retry.call_with_retry(post.post_id, _attempt)

    async def delete_post(self, platform_post_id: str) -> bool:
        """Delete a Buffer post by its platform post ID."""
        if not self._live:
            logger.info("[Publisher][DRY-RUN] delete %s skipped", platform_post_id)
            return True
        try:
            await self._rate_limiter.acquire()
            result = await self._client.delete(f"updates/{platform_post_id}.json")
            return result.get("success", False)
        except BufferAPIError as exc:
            logger.error("[Publisher] Failed to delete post %s: %s", platform_post_id, exc)
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _triple_lock_check(
        self,
        post: BufferPost,
        governance_approved: bool,
        operator_approved: bool,
        rights_status: str,
    ) -> None:
        allowed_rights = {"owned", "licensed", "public_source"}
        if not governance_approved:
            raise PublishApprovalError(f"Post {post.post_id} blocked: governance not approved")
        if not operator_approved:
            raise PublishApprovalError(f"Post {post.post_id} blocked: operator approval required")
        if rights_status not in allowed_rights:
            raise PublishApprovalError(
                f"Post {post.post_id} blocked: rights_status={rights_status!r} not in {allowed_rights}"
            )

    def _validate_media(self, media_url: str) -> None:
        """Validate local media file if url is a filesystem path."""
        if not media_url.startswith("/") and not media_url.startswith("./"):
            return  # remote URL — skip local validation
        path = Path(media_url)
        if not path.exists():
            raise MediaValidationError(f"Media file not found: {media_url}")
        if path.stat().st_size == 0:
            raise MediaValidationError(f"Media file is empty (0 bytes): {media_url}")
        # Checksum (just verify we can read it)
        try:
            h = hashlib.sha256()
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        except OSError as exc:
            raise MediaValidationError(f"Media file unreadable: {media_url}: {exc}") from exc

    async def _call_create_update(self, post: BufferPost, profile_id: str) -> BufferPublishResult:
        """Route to GraphQL (API Key tokens) or REST (legacy OAuth tokens)."""
        from sfc.connectors.buffer.graphql_client import BufferGraphQLClient
        token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        if BufferGraphQLClient.is_api_key(token):
            return await self._call_graphql_create_post(post, profile_id)
        return await self._call_rest_create_update(post, profile_id)

    async def _call_graphql_create_post(self, post: BufferPost, profile_id: str) -> BufferPublishResult:
        """Create a post via the Buffer GraphQL API (required for API Key tokens)."""
        from sfc.connectors.buffer.graphql_client import BufferGraphQLClient, BufferGraphQLError

        gql_client = BufferGraphQLClient()  # fresh — reads LIVE_PUBLISHING_ENABLED now
        scheduled_at = post.scheduled_at.isoformat() if post.scheduled_at else None

        try:
            post_data = await gql_client.create_post(
                channel_id=profile_id,
                text=self._build_text(post),
                scheduled_at=scheduled_at,
            )
        except BufferGraphQLError as exc:
            raise BufferAPIError(str(exc), status_code=exc.status_code, permanent=exc.permanent) from exc

        if post_data.get("dry_run"):
            return self._dry_run_result(post)

        buffer_post_id = str(post_data.get("id", ""))
        if not buffer_post_id:
            raise BufferAPIError("GraphQL createPost returned no post ID — creation unconfirmed", permanent=False)

        post.status = BufferPostStatus.SCHEDULED
        post.platform_post_id = buffer_post_id
        post.published_at = datetime.utcnow() if not post.scheduled_at else None

        logger.info("[Publisher] Post created via GraphQL — platform=%s buffer_id=%s", post.platform.value, buffer_post_id)
        return BufferPublishResult(
            post_id=post.post_id,
            platform=post.platform,
            platform_post_id=buffer_post_id,
            status=BufferPostStatus.SCHEDULED,
            url=f"https://buffer.com/p/{buffer_post_id}",
        )

    async def _call_rest_create_update(self, post: BufferPost, profile_id: str) -> BufferPublishResult:
        """Create a post via the Buffer REST API v1 (legacy OAuth tokens only)."""
        data: dict[str, Any] = {
            "profile_ids[]": profile_id,
            "text": self._build_text(post),
        }
        if post.scheduled_at:
            data["scheduled_at"] = post.scheduled_at.isoformat()
            data["now"] = "false"
        else:
            data["now"] = "true"
        if post.media_url:
            data["media[link]"] = post.media_url

        response = await self._client.post("updates/create.json", data=data)

        updates = response.get("updates", [])
        if not updates:
            raise BufferAPIError("Buffer returned no post IDs — creation unconfirmed", permanent=False)

        buffer_post_id = str(updates[0].get("id", ""))
        if not buffer_post_id:
            raise BufferAPIError("Buffer returned empty post ID — creation unconfirmed", permanent=False)

        post.status = BufferPostStatus.SCHEDULED
        post.platform_post_id = buffer_post_id
        post.published_at = datetime.utcnow() if not post.scheduled_at else None

        logger.info("[Publisher] Post created via REST — platform=%s buffer_id=%s", post.platform.value, buffer_post_id)
        return BufferPublishResult(
            post_id=post.post_id,
            platform=post.platform,
            platform_post_id=buffer_post_id,
            status=BufferPostStatus.SCHEDULED,
            url=f"https://buffer.com/p/{buffer_post_id}",
        )

    def _build_text(self, post: BufferPost) -> str:
        text = post.content
        if post.hashtags:
            text = text.rstrip() + "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in post.hashtags)
        return text

    def _dry_run_result(self, post: BufferPost) -> BufferPublishResult:
        dry_id = f"dry_{post.post_id[:8]}"
        logger.info(
            "[Publisher][DRY-RUN] Post would be created — platform=%s dry_id=%s",
            post.platform.value, dry_id,
        )
        post.status = BufferPostStatus.SCHEDULED
        post.platform_post_id = dry_id
        return BufferPublishResult(
            post_id=post.post_id,
            platform=post.platform,
            platform_post_id=dry_id,
            status=BufferPostStatus.SCHEDULED,
            url=f"https://buffer.com/dry-run/{dry_id}",
        )


_singleton: BufferPublisher | None = None


def get_buffer_publisher() -> BufferPublisher:
    global _singleton
    if _singleton is None:
        _singleton = BufferPublisher()
    return _singleton
