"""Tests for Package 9B — Buffer real API modules (dry-run mode)."""

from __future__ import annotations

import asyncio
import os
import pytest

from sfc.connectors.buffer.api_client import BufferAPIClient, BufferAPIError
from sfc.connectors.buffer.auth import BufferAuth
from sfc.connectors.buffer.models import BufferPlatform, BufferPost, BufferPostStatus
from sfc.connectors.buffer.profiles import BufferProfileManager
from sfc.connectors.buffer.publisher import BufferPublisher, PublishApprovalError, MediaValidationError
from sfc.connectors.buffer.rate_limits import BufferRateLimiter
from sfc.connectors.buffer.retry_manager import BufferRetryManager
from sfc.connectors.buffer.scheduler import BufferScheduler


# ---------------------------------------------------------------------------
# BufferAPIClient — dry-run
# ---------------------------------------------------------------------------

class TestBufferAPIClientDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        self.client = BufferAPIClient()

    def test_is_not_live_by_default(self) -> None:
        assert self.client.is_live is False

    @pytest.mark.asyncio
    async def test_get_returns_dry_run(self) -> None:
        result = await self.client.get("user.json")
        assert result.get("dry_run") is True
        assert result.get("method") == "GET"

    @pytest.mark.asyncio
    async def test_post_returns_dry_run(self) -> None:
        result = await self.client.post("updates/create.json", data={"text": "hello"})
        assert result.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_delete_returns_dry_run(self) -> None:
        result = await self.client.delete("updates/abc123.json")
        assert result.get("dry_run") is True

    def test_has_token_false_when_no_env(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)
        client = BufferAPIClient()
        assert client.has_token is False


# ---------------------------------------------------------------------------
# BufferAuth — dry-run
# ---------------------------------------------------------------------------

class TestBufferAuthDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        os.environ["BUFFER_ACCESS_TOKEN"] = "test_token_dry"

    def teardown_method(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)

    @pytest.mark.asyncio
    async def test_validate_token_dry_run(self) -> None:
        client = BufferAPIClient()
        auth = BufferAuth(client=client)
        result = await auth.validate_token()
        assert result is True
        assert auth.is_authenticated is True

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self) -> None:
        client = BufferAPIClient()
        auth = BufferAuth(client=client)
        health = await auth.health_check()
        assert health["ok"] is True
        assert health["has_token"] is True

    @pytest.mark.asyncio
    async def test_no_token_returns_false(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)
        auth = BufferAuth()
        result = await auth.validate_token()
        assert result is False


# ---------------------------------------------------------------------------
# BufferProfileManager — dry-run
# ---------------------------------------------------------------------------

class TestBufferProfilesDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        os.environ["BUFFER_X_PROFILE_ID"] = "x_profile_123"

    def teardown_method(self) -> None:
        os.environ.pop("BUFFER_X_PROFILE_ID", None)

    @pytest.mark.asyncio
    async def test_get_profiles_dry_run(self) -> None:
        mgr = BufferProfileManager()
        profiles = await mgr.get_profiles()
        assert isinstance(profiles, list)

    @pytest.mark.asyncio
    async def test_get_profile_id_from_env(self) -> None:
        mgr = BufferProfileManager()
        pid = await mgr.get_profile_id("x")
        assert pid == "x_profile_123"

    @pytest.mark.asyncio
    async def test_unknown_platform_returns_none(self) -> None:
        mgr = BufferProfileManager()
        pid = await mgr.get_profile_id("snapchat")
        assert pid is None


# ---------------------------------------------------------------------------
# BufferRateLimiter
# ---------------------------------------------------------------------------

class TestBufferRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_decrements_quota(self) -> None:
        limiter = BufferRateLimiter(max_requests=10)
        await limiter.acquire()
        assert limiter.state.remaining_quota == 9

    def test_record_429_zeroes_quota(self) -> None:
        limiter = BufferRateLimiter(max_requests=10)
        limiter.record_429(retry_after_seconds=5)
        assert limiter.state.remaining_quota == 0
        assert limiter.is_throttled is True

    def test_update_from_headers(self) -> None:
        limiter = BufferRateLimiter()
        limiter.update_from_headers({"x-ratelimit-remaining": "50"})
        assert limiter.state.remaining_quota == 50


# ---------------------------------------------------------------------------
# BufferRetryManager
# ---------------------------------------------------------------------------

class TestBufferRetryManager:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        manager = BufferRetryManager(delays_seconds=[1, 2])

        async def always_ok() -> str:
            return "ok"

        result = await manager.call_with_retry("test1", always_ok)
        assert result == "ok"
        assert manager.get_record("test1").succeeded is True

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self) -> None:
        manager = BufferRetryManager(delays_seconds=[0, 0])
        call_count = 0

        async def fails_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise BufferAPIError("transient", status_code=500, permanent=False)
            return "ok"

        result = await manager.call_with_retry("test2", fails_once, skip_wait=True)
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_permanent_error_not_retried(self) -> None:
        manager = BufferRetryManager(delays_seconds=[0, 0])
        call_count = 0

        async def always_perm_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise BufferAPIError("forbidden", status_code=403, permanent=True)

        with pytest.raises(BufferAPIError):
            await manager.call_with_retry("test3", always_perm_fail, skip_wait=True)
        assert call_count == 1  # no retries on permanent error

    @pytest.mark.asyncio
    async def test_exhausted_after_max_retries(self) -> None:
        manager = BufferRetryManager(delays_seconds=[0])

        async def always_fail() -> None:
            raise BufferAPIError("server error", status_code=500, permanent=False)

        with pytest.raises(BufferAPIError):
            await manager.call_with_retry("test4", always_fail, skip_wait=True)
        assert manager.get_record("test4").exhausted is True


# ---------------------------------------------------------------------------
# BufferPublisher — triple-lock gate
# ---------------------------------------------------------------------------

class TestBufferPublisherApprovalGate:
    def _make_post(self) -> BufferPost:
        return BufferPost(
            content="Goal! Al-Hilal scores!",
            platform=BufferPlatform.X,
            hashtags=["AlHilal", "SPL"],
        )

    @pytest.mark.asyncio
    async def test_blocks_when_governance_not_approved(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        publisher = BufferPublisher()
        post = self._make_post()
        with pytest.raises(PublishApprovalError, match="governance"):
            await publisher.create_post(
                post, "profile_x",
                governance_approved=False,
                operator_approved=True,
                rights_status="owned",
            )

    @pytest.mark.asyncio
    async def test_blocks_when_operator_not_approved(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        publisher = BufferPublisher()
        post = self._make_post()
        with pytest.raises(PublishApprovalError, match="operator"):
            await publisher.create_post(
                post, "profile_x",
                governance_approved=True,
                operator_approved=False,
                rights_status="owned",
            )

    @pytest.mark.asyncio
    async def test_blocks_when_rights_restricted(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        publisher = BufferPublisher()
        post = self._make_post()
        with pytest.raises(PublishApprovalError, match="rights_status"):
            await publisher.create_post(
                post, "profile_x",
                governance_approved=True,
                operator_approved=True,
                rights_status="restricted",
            )

    @pytest.mark.asyncio
    async def test_dry_run_returns_result_with_dry_id(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        publisher = BufferPublisher()
        post = self._make_post()
        result = await publisher.create_post(
            post, "profile_x",
            governance_approved=True,
            operator_approved=True,
            rights_status="owned",
        )
        assert result.platform_post_id.startswith("dry_")
        assert result.status == BufferPostStatus.SCHEDULED


# ---------------------------------------------------------------------------
# BufferScheduler
# ---------------------------------------------------------------------------

class TestBufferScheduler:
    def test_next_slot_for_x(self) -> None:
        scheduler = BufferScheduler()
        slot = scheduler.next_slot("x")
        from datetime import datetime
        assert slot > datetime.utcnow()

    def test_schedule_posts_assigns_scheduled_at(self) -> None:
        scheduler = BufferScheduler()
        posts = [
            BufferPost(content="post1", platform=BufferPlatform.X),
            BufferPost(content="post2", platform=BufferPlatform.X),
        ]
        scheduled = scheduler.schedule_posts(posts)
        assert all(p.scheduled_at is not None for p in scheduled)
        # Second post should be after first
        assert scheduled[1].scheduled_at > scheduled[0].scheduled_at  # type: ignore[operator]

    def test_build_campaign_schedule(self) -> None:
        scheduler = BufferScheduler()
        items = [{"content": "Match highlight!", "media_url": "", "hashtags": ["SPL"]}]
        schedule = scheduler.build_campaign_schedule(items, ["x", "youtube"])
        assert len(schedule) == 2
        platforms = {s["platform"] for s in schedule}
        assert "x" in platforms and "youtube" in platforms
