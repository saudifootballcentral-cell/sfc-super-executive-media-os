"""Tests for Buffer GraphQL connector — token validation, profile discovery, fallback."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sfc.connectors.buffer.api_client import BufferAPIClient
from sfc.connectors.buffer.auth import BufferAuth, BufferUser
from sfc.connectors.buffer.graphql_client import (
    BufferGraphQLChannel,
    BufferGraphQLClient,
    BufferGraphQLError,
    BufferGraphQLUser,
)
from sfc.connectors.buffer.profiles import BufferProfile, BufferProfileManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gql_client(live: bool = False, token: str = "test-api-key-abc") -> BufferGraphQLClient:
    client = BufferGraphQLClient.__new__(BufferGraphQLClient)
    client._token = token
    client._url = "https://api.bufferapp.com/graphql"
    client._timeout = 30.0
    client._live = live
    return client


def _make_rest_client(live: bool = False, token: str = "test-api-key-abc") -> BufferAPIClient:
    client = BufferAPIClient.__new__(BufferAPIClient)
    client._token = token
    client._base_url = "https://api.bufferapp.com/1"
    client._timeout = 30.0
    client._live = live
    return client


# ---------------------------------------------------------------------------
# BufferGraphQLClient — token type detection
# ---------------------------------------------------------------------------

class TestAPIKeyDetection:
    def test_hyphenated_token_is_api_key(self) -> None:
        assert BufferGraphQLClient.is_api_key("WB3L8sijPjyBqUpPCPuEFP2M-IPF2n8D5sbC311X1Rm") is True

    def test_plain_alphanumeric_is_not_api_key(self) -> None:
        assert BufferGraphQLClient.is_api_key("abc123def456ghi789") is False

    def test_empty_token_is_not_api_key(self) -> None:
        assert BufferGraphQLClient.is_api_key("") is False

    def test_multiple_hyphens_is_api_key(self) -> None:
        assert BufferGraphQLClient.is_api_key("tok-en-with-hyphens") is True


# ---------------------------------------------------------------------------
# BufferGraphQLClient — dry-run mode
# ---------------------------------------------------------------------------

class TestBufferGraphQLClientDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        os.environ["BUFFER_ACCESS_TOKEN"] = "test-graphql-key-dryrun"

    def teardown_method(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    @pytest.mark.asyncio
    async def test_validate_dry_run_returns_stub_user(self) -> None:
        client = _make_gql_client(live=False)
        user = await client.validate()
        assert user is not None
        assert user.api_mode == "graphql"
        assert user.raw.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_query_dry_run_returns_dry_run_flag(self) -> None:
        client = _make_gql_client(live=False)
        result = await client.query("{ account { id } }")
        assert result.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_get_channels_dry_run_returns_empty(self) -> None:
        client = _make_gql_client(live=False)
        channels = await client.get_channels()
        assert channels == []

    def test_has_token_true_when_set(self) -> None:
        client = _make_gql_client(token="some-api-key-xyz")
        assert client.has_token is True

    def test_has_token_false_when_empty(self) -> None:
        client = _make_gql_client(token="")
        assert client.has_token is False

    @pytest.mark.asyncio
    async def test_validate_returns_none_when_no_token(self) -> None:
        client = _make_gql_client(live=False, token="")
        user = await client.validate()
        assert user is None


# ---------------------------------------------------------------------------
# BufferGraphQLClient — live mode (mocked HTTP)
# ---------------------------------------------------------------------------

class TestBufferGraphQLClientLive:
    @pytest.mark.asyncio
    async def test_validate_returns_user_on_success(self) -> None:
        client = _make_gql_client(live=True, token="live-api-key-abc")
        mock_response = {
            "account": {
                "id": "user123",
                "name": "SFC Media",
                "email": "sfc@example.com",
                "timezone": "Asia/Riyadh",
                "channels": [],
            }
        }
        with patch.object(client, "query", new=AsyncMock(return_value=mock_response)):
            user = await client.validate()
        assert user is not None
        assert user.user_id == "user123"
        assert user.name == "SFC Media"
        assert user.email == "sfc@example.com"
        assert user.timezone == "Asia/Riyadh"
        assert user.api_mode == "graphql"

    @pytest.mark.asyncio
    async def test_validate_returns_none_when_account_empty(self) -> None:
        # Buffer schema uses `account` — there is no `currentUser` fallback.
        # When account data is missing, validate() returns None (no retry).
        client = _make_gql_client(live=True, token="live-api-key-abc")
        call_count = 0

        async def mock_query(gql: str, variables: Any = None) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {}  # no account field

        with patch.object(client, "query", side_effect=mock_query):
            user = await client.validate()
        assert user is None
        assert call_count == 1  # single query, no fallback

    @pytest.mark.asyncio
    async def test_validate_returns_none_on_auth_error(self) -> None:
        client = _make_gql_client(live=True, token="bad-key-xxx")
        with patch.object(
            client, "query",
            new=AsyncMock(side_effect=BufferGraphQLError("Unauthorized", status_code=401, permanent=True))
        ):
            user = await client.validate()
        assert user is None

    @pytest.mark.asyncio
    async def test_get_channels_parses_list(self) -> None:
        # get_channels() is two-step: first fetch org IDs, then fetch channels per org.
        # Channel type no longer has "handle"; "name" carries the platform username.
        client = _make_gql_client(live=True, token="live-api-key-abc")

        # Responses indexed by call order: [0]=account/org query, [1]=channels query
        responses = [
            # Step 1: account with one org
            {"account": {"id": "acct1", "name": "SFC", "email": "sfc@x.com", "timezone": "UTC",
                         "organizations": [{"id": "org1", "name": "SFC Org"}]}},
            # Step 2: channels for org1
            {"channels": [
                {"id": "ch1", "service": "twitter", "name": "@sfc_x", "displayName": "SFC X", "avatar": "", "isQueuePaused": False},
                {"id": "ch2", "service": "instagram", "name": "@sfc_ig", "displayName": "SFC IG", "avatar": "", "isQueuePaused": False},
            ]},
        ]
        call_count = 0

        async def mock_query(gql: str, variables: Any = None) -> dict[str, Any]:
            nonlocal call_count
            result = responses[call_count]
            call_count += 1
            return result

        with patch.object(client, "query", side_effect=mock_query):
            channels = await client.get_channels()

        assert len(channels) == 2
        assert channels[0].channel_id == "ch1"
        assert channels[0].service == "twitter"
        assert channels[0].name == "@sfc_x"
        assert channels[0].display_name == "SFC X"
        assert channels[0].handle == "@sfc_x"  # property alias for name
        assert channels[1].service == "instagram"
        assert call_count == 2


# ---------------------------------------------------------------------------
# BufferAuth — GraphQL token validation
# ---------------------------------------------------------------------------

class TestBufferAuthGraphQL:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        os.environ["BUFFER_ACCESS_TOKEN"] = "test-api-key-dryrun"

    def teardown_method(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    @pytest.mark.asyncio
    async def test_validate_dry_run_returns_true(self) -> None:
        rest = _make_rest_client(live=False)
        gql = _make_gql_client(live=False)
        auth = BufferAuth(client=rest, graphql_client=gql)
        result = await auth.validate_token()
        assert result is True
        assert auth.is_authenticated is True

    @pytest.mark.asyncio
    async def test_api_key_token_tries_graphql_first(self) -> None:
        rest = _make_rest_client(live=True, token="live-api-key-abc")
        gql = _make_gql_client(live=True, token="live-api-key-abc")
        auth = BufferAuth(client=rest, graphql_client=gql)
        gql_user = BufferGraphQLUser(
            user_id="u1", name="SFC", email="sfc@x.com", timezone="UTC", raw={}
        )
        with patch.object(gql, "validate", new=AsyncMock(return_value=gql_user)):
            result = await auth.validate_token()
        assert result is True
        assert auth.api_mode == "graphql"

    @pytest.mark.asyncio
    async def test_graphql_failure_falls_back_to_rest(self) -> None:
        rest = _make_rest_client(live=True, token="live-api-key-abc")
        gql = _make_gql_client(live=True, token="live-api-key-abc")
        auth = BufferAuth(client=rest, graphql_client=gql)
        rest_response = {"_id": "u2", "name": "REST User", "email": "r@x.com", "plan": "free", "timezone": "UTC"}
        with patch.object(gql, "validate", new=AsyncMock(return_value=None)):
            with patch.object(rest, "get", new=AsyncMock(return_value=rest_response)):
                result = await auth.validate_token()
        assert result is True
        assert auth.api_mode == "rest"

    @pytest.mark.asyncio
    async def test_no_token_returns_false(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)
        auth = BufferAuth()
        result = await auth.validate_token()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_includes_api_mode(self) -> None:
        rest = _make_rest_client(live=False)
        gql = _make_gql_client(live=False)
        auth = BufferAuth(client=rest, graphql_client=gql)
        health = await auth.health_check()
        assert "api_mode" in health
        assert "is_api_key" in health
        assert health["ok"] is True

    @pytest.mark.asyncio
    async def test_invalid_token_both_paths_fail(self) -> None:
        rest = _make_rest_client(live=True, token="bad-key-invalid")
        gql = _make_gql_client(live=True, token="bad-key-invalid")
        auth = BufferAuth(client=rest, graphql_client=gql)
        with patch.object(gql, "validate", new=AsyncMock(return_value=None)):
            with patch.object(rest, "get", new=AsyncMock(side_effect=Exception("401 Unauthorized"))):
                result = await auth.validate_token()
        assert result is False
        assert auth.is_authenticated is False


# ---------------------------------------------------------------------------
# BufferProfileManager — GraphQL channel discovery
# ---------------------------------------------------------------------------

class TestBufferProfileManagerGraphQL:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)
        os.environ["BUFFER_ACCESS_TOKEN"] = "test-api-key-profiles"
        # Clear env profile overrides so GraphQL/REST paths are exercised
        for var in (
            "BUFFER_X_PROFILE_ID", "BUFFER_YOUTUBE_PROFILE_ID",
            "BUFFER_INSTAGRAM_PROFILE_ID", "BUFFER_TIKTOK_PROFILE_ID",
            "BUFFER_FACEBOOK_PROFILE_ID", "BUFFER_THREADS_PROFILE_ID",
            "BUFFER_LINKEDIN_PROFILE_ID",
        ):
            os.environ.pop(var, None)

    def teardown_method(self) -> None:
        os.environ.pop("BUFFER_ACCESS_TOKEN", None)

    @pytest.mark.asyncio
    async def test_graphql_channels_populate_profiles(self) -> None:
        rest = _make_rest_client(live=True, token="test-api-key-profiles")
        gql = _make_gql_client(live=True, token="test-api-key-profiles")
        mgr = BufferProfileManager(client=rest, graphql_client=gql)
        channels = [
            BufferGraphQLChannel("ch1", "twitter", "SFC X", "@sfc_x", "", {}),
            BufferGraphQLChannel("ch2", "instagram", "SFC IG", "@sfc_ig", "", {}),
        ]
        with patch.object(gql, "get_channels", new=AsyncMock(return_value=channels)):
            profiles = await mgr.get_profiles(force_refresh=True)
        assert len(profiles) == 2
        assert all(p.source == "graphql" for p in profiles)
        keys = {p.platform_key for p in profiles}
        assert "x" in keys
        assert "instagram" in keys

    @pytest.mark.asyncio
    async def test_graphql_failure_falls_back_to_rest(self) -> None:
        rest = _make_rest_client(live=True, token="test-api-key-profiles")
        gql = _make_gql_client(live=True, token="test-api-key-profiles")
        mgr = BufferProfileManager(client=rest, graphql_client=gql)
        rest_profiles = [
            {"_id": "r1", "service": "twitter", "service_username": "sfc", "formatted_username": "@sfc",
             "formatted_service": "Twitter", "avatar": "", "timezone": "UTC", "utc_offset": 0}
        ]
        # Simulate real failure: get_channels raises (network error, 401, etc.)
        with patch.object(gql, "get_channels", new=AsyncMock(side_effect=Exception("GraphQL unavailable"))):
            with patch.object(rest, "get", new=AsyncMock(return_value=rest_profiles)):
                profiles = await mgr.get_profiles(force_refresh=True)
        assert len(profiles) == 1
        assert profiles[0].source == "rest"

    @pytest.mark.asyncio
    async def test_dry_run_returns_env_stubs(self) -> None:
        os.environ["BUFFER_X_PROFILE_ID"] = "x_test_123"
        rest = _make_rest_client(live=False, token="test-api-key-profiles")
        gql = _make_gql_client(live=False, token="test-api-key-profiles")
        mgr = BufferProfileManager(client=rest, graphql_client=gql)
        profiles = await mgr.get_profiles(force_refresh=True)
        profile_ids = {p.profile_id for p in profiles}
        assert "x_test_123" in profile_ids
        assert all(p.source == "env" for p in profiles)
        os.environ.pop("BUFFER_X_PROFILE_ID", None)

    @pytest.mark.asyncio
    async def test_gql_service_map_normalises_twitter_to_x(self) -> None:
        rest = _make_rest_client(live=True, token="test-api-key-profiles")
        gql = _make_gql_client(live=True, token="test-api-key-profiles")
        mgr = BufferProfileManager(client=rest, graphql_client=gql)
        channels = [BufferGraphQLChannel("ch1", "twitter", "SFC", "@sfc", "", {})]
        with patch.object(gql, "get_channels", new=AsyncMock(return_value=channels)):
            profiles = await mgr.get_profiles(force_refresh=True)
        assert profiles[0].platform_key == "x"
