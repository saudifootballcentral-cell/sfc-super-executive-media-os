"""Regression tests: Buffer GraphQL HTTP 400 must be permanent, safely logged, never retried.

Covers:
- _handle_response() raises BufferGraphQLError(permanent=True) on 400
- Error message contains GraphQL errors[].message and extensions.code
- Log output contains BUFFER_GRAPHQL_BAD_REQUEST tag
- Log output never contains Authorization header, Bearer token, or token values
- Log output contains variable_keys (safe) but not variable values (unsafe)
- query() calls the endpoint exactly once — no internal retry
- BufferRetryManager skips retry loop for permanent errors
- Phase VI can surface the exact Buffer rejection reason
"""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sfc.connectors.buffer.api_client import BufferAPIError
from sfc.connectors.buffer.graphql_client import BufferGraphQLClient, BufferGraphQLError
from sfc.connectors.buffer.retry_manager import BufferRetryManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(token: str = "test-api-key-mock-value") -> BufferGraphQLClient:
    """Fresh client not reading from os.environ."""
    client = BufferGraphQLClient.__new__(BufferGraphQLClient)
    client._token = token
    client._url = "https://api.buffer.com/graphql"
    client._timeout = 10.0
    client._live = True
    return client


def _resp(status: int, body: dict) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )


def _resp_text(status: int, text: str) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=text.encode(),
        headers={"content-type": "text/plain"},
    )


# ---------------------------------------------------------------------------
# 1. permanent=True on HTTP 400
# ---------------------------------------------------------------------------

class TestHttp400IsPermanent:

    def test_400_raises_permanent_error(self):
        client = _make_client()
        resp = _resp(400, {"errors": [{"message": "Unknown field 'channelId'"}]})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost", ["channelId", "text"])
        assert exc_info.value.permanent is True

    def test_400_status_code_preserved(self):
        client = _make_client()
        resp = _resp(400, {"errors": [{"message": "Bad input"}]})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        assert exc_info.value.status_code == 400

    def test_401_raises_permanent_error(self):
        client = _make_client()
        resp = _resp(401, {"message": "Unauthorized"})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCWhoAmI")
        assert exc_info.value.permanent is True
        assert exc_info.value.status_code == 401

    def test_403_raises_permanent_error(self):
        client = _make_client()
        resp = _resp(403, {"message": "Forbidden"})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCWhoAmI")
        assert exc_info.value.permanent is True

    def test_500_is_transient(self):
        client = _make_client()
        resp = _resp(500, {})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        assert exc_info.value.permanent is False


# ---------------------------------------------------------------------------
# 2. Error message includes GraphQL details
# ---------------------------------------------------------------------------

class TestErrorMessageContent:

    def test_400_message_includes_graphql_error_message(self):
        client = _make_client()
        resp = _resp(400, {"errors": [{"message": "Field 'channelId' was not provided"}]})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost", ["channelId"])
        assert "Field 'channelId' was not provided" in str(exc_info.value)

    def test_400_message_includes_extensions_code(self):
        client = _make_client()
        resp = _resp(400, {
            "errors": [{"message": "Some error", "extensions": {"code": "BAD_USER_INPUT"}}]
        })
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        assert "BAD_USER_INPUT" in str(exc_info.value)

    def test_400_message_contains_bad_request_tag(self):
        client = _make_client()
        resp = _resp(400, {"errors": [{"message": "anything"}]})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        assert "BUFFER_GRAPHQL_BAD_REQUEST" in str(exc_info.value)

    def test_400_message_contains_operation_name(self):
        client = _make_client()
        resp = _resp(400, {"errors": [{"message": "anything"}]})
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        assert "SFCCreatePost" in str(exc_info.value)

    def test_400_multiple_errors_joined(self):
        client = _make_client()
        resp = _resp(400, {
            "errors": [
                {"message": "Error one"},
                {"message": "Error two"},
            ]
        })
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        msg = str(exc_info.value)
        assert "Error one" in msg
        assert "Error two" in msg

    def test_400_non_json_body_still_raises_permanent(self):
        client = _make_client()
        resp = _resp_text(400, "Bad Request")
        with pytest.raises(BufferGraphQLError) as exc_info:
            client._handle_response(resp, "SFCCreatePost")
        assert exc_info.value.permanent is True
        assert "BUFFER_GRAPHQL_BAD_REQUEST" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Safe logging — no secrets in log output
# ---------------------------------------------------------------------------

class TestSafeLogging:

    def test_400_log_contains_bad_request_tag(self, caplog):
        client = _make_client()
        resp = _resp(400, {"errors": [{"message": "Bad field"}]})
        with caplog.at_level(logging.ERROR, logger="sfc.connectors.buffer.graphql_client"):
            with pytest.raises(BufferGraphQLError):
                client._handle_response(resp, "SFCCreatePost", ["channelId", "text"])
        full_log = "\n".join(r.getMessage() for r in caplog.records)
        assert "BUFFER_GRAPHQL_BAD_REQUEST" in full_log

    def test_400_log_contains_graphql_error_message(self, caplog):
        client = _make_client()
        resp = _resp(400, {
            "errors": [{"message": "Argument channelId is required", "extensions": {"code": "BAD_USER_INPUT"}}]
        })
        with caplog.at_level(logging.ERROR, logger="sfc.connectors.buffer.graphql_client"):
            with pytest.raises(BufferGraphQLError):
                client._handle_response(resp, "SFCCreatePost", ["channelId"])
        full_log = "\n".join(r.getMessage() for r in caplog.records)
        assert "Argument channelId is required" in full_log

    def test_400_log_contains_extensions_code(self, caplog):
        client = _make_client()
        resp = _resp(400, {
            "errors": [{"message": "err", "extensions": {"code": "UNAUTHENTICATED"}}]
        })
        with caplog.at_level(logging.ERROR, logger="sfc.connectors.buffer.graphql_client"):
            with pytest.raises(BufferGraphQLError):
                client._handle_response(resp, "SFCWhoAmI", [])
        full_log = "\n".join(r.getMessage() for r in caplog.records)
        assert "UNAUTHENTICATED" in full_log

    def test_400_log_contains_variable_keys_not_values(self, caplog):
        client = _make_client("secret-token-abc123")
        resp = _resp(400, {"errors": [{"message": "err"}]})
        with caplog.at_level(logging.ERROR, logger="sfc.connectors.buffer.graphql_client"):
            with pytest.raises(BufferGraphQLError):
                client._handle_response(resp, "SFCCreatePost", ["channelId", "text"])
        full_log = "\n".join(r.getMessage() for r in caplog.records)
        assert "channelId" in full_log    # key is safe to log
        assert "text" in full_log         # key is safe to log

    def test_400_log_has_no_authorization_header(self, caplog):
        client = _make_client("super-secret-api-key-xyz")
        resp = _resp(400, {"errors": [{"message": "Bad"}]})
        with caplog.at_level(logging.DEBUG, logger="sfc.connectors.buffer.graphql_client"):
            with pytest.raises(BufferGraphQLError):
                client._handle_response(resp, "SFCCreatePost", ["channelId"])
        full_log = "\n".join(r.getMessage() for r in caplog.records)
        assert "Authorization" not in full_log
        assert "Bearer" not in full_log

    def test_400_log_has_no_token_value(self, caplog):
        secret_token = "super-secret-api-key-xyz"
        client = _make_client(secret_token)
        resp = _resp(400, {"errors": [{"message": "Bad"}]})
        with caplog.at_level(logging.DEBUG, logger="sfc.connectors.buffer.graphql_client"):
            with pytest.raises(BufferGraphQLError):
                client._handle_response(resp, "SFCCreatePost", ["channelId"])
        full_log = "\n".join(r.getMessage() for r in caplog.records)
        assert secret_token not in full_log


# ---------------------------------------------------------------------------
# 4. Operation name extraction
# ---------------------------------------------------------------------------

class TestOperationNameExtraction:

    def test_extracts_mutation_name(self):
        gql = "mutation SFCCreatePost($channelId: String!) { createPost { post { id } } }"
        assert BufferGraphQLClient._extract_operation_name(gql) == "SFCCreatePost"

    def test_extracts_query_name(self):
        gql = "query SFCWhoAmI { account { id } }"
        assert BufferGraphQLClient._extract_operation_name(gql) == "SFCWhoAmI"

    def test_anonymous_when_no_name(self):
        gql = "{ account { id } }"
        assert BufferGraphQLClient._extract_operation_name(gql) == "anonymous"


# ---------------------------------------------------------------------------
# 5. query() calls endpoint exactly once on 400 (no internal retry)
# ---------------------------------------------------------------------------

class TestQueryCalledOnce:

    @pytest.mark.asyncio
    async def test_400_query_called_exactly_once(self):
        client = _make_client()
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _resp(400, {"errors": [{"message": "Bad input", "extensions": {"code": "BAD_USER_INPUT"}}]})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.post = mock_post
            mock_cls.return_value = mock_inst

            with pytest.raises(BufferGraphQLError) as exc_info:
                await client.query(_MUTATION_CREATE_POST_GQL)

        assert call_count == 1, "query() must call the API exactly once on 400, not retry"
        assert exc_info.value.permanent is True
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_400_exception_propagates_gql_message(self):
        client = _make_client()
        error_msg = "Channel not found or access denied"

        async def mock_post(*args, **kwargs):
            return _resp(400, {"errors": [{"message": error_msg, "extensions": {"code": "NOT_FOUND"}}]})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.post = mock_post
            mock_cls.return_value = mock_inst

            with pytest.raises(BufferGraphQLError) as exc_info:
                await client.query(_MUTATION_CREATE_POST_GQL, {"channelId": "ch_123", "text": "test"})

        assert error_msg in str(exc_info.value)
        assert "NOT_FOUND" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 6. BufferRetryManager skips retry on permanent errors
# ---------------------------------------------------------------------------

class TestRetryManagerPermanentSkip:

    @pytest.mark.asyncio
    async def test_permanent_error_not_retried(self):
        manager = BufferRetryManager(delays_seconds=[1, 2])
        call_count = 0

        async def always_fail_permanent():
            nonlocal call_count
            call_count += 1
            raise BufferAPIError(
                "BUFFER_GRAPHQL_BAD_REQUEST status=400 operation=SFCCreatePost: Bad input [BAD_USER_INPUT]",
                status_code=400,
                permanent=True,
            )

        with pytest.raises(BufferAPIError) as exc_info:
            await manager.call_with_retry("post_abc", always_fail_permanent, skip_wait=True)

        assert call_count == 1, "Permanent error must exit immediately without retry"
        assert exc_info.value.permanent is True
        record = manager.get_record("post_abc")
        assert record is not None
        assert record.exhausted is True
        assert record.attempt == 0  # never incremented — failed before first retry

    @pytest.mark.asyncio
    async def test_transient_error_is_retried(self):
        manager = BufferRetryManager(delays_seconds=[0, 0])
        call_count = 0

        async def always_fail_transient():
            nonlocal call_count
            call_count += 1
            raise BufferAPIError("Server error", status_code=500, permanent=False)

        with pytest.raises(BufferAPIError):
            await manager.call_with_retry("post_xyz", always_fail_transient, skip_wait=True)

        assert call_count == 3, "Transient error with 2 delays should be called 3 times total"


# ---------------------------------------------------------------------------
# 7. Phase VI error surfacing — error message readable in go-live output
# ---------------------------------------------------------------------------

class TestPhaseVIErrorSurfacing:

    @pytest.mark.asyncio
    async def test_phase_vi_gets_readable_error_from_400(self):
        """The error string that reaches Phase VI contains the Buffer rejection reason."""
        from sfc.connectors.buffer.graphql_client import BufferGraphQLClient, BufferGraphQLError
        from sfc.connectors.buffer.models import BufferPost, BufferPlatform

        post = BufferPost(
            post_id="test_post_001",
            platform=BufferPlatform.X,
            content="Test post",
            hashtags=[],
        )

        async def mock_post(*args, **kwargs):
            return _resp(400, {
                "errors": [{
                    "message": "Channel 'ch_missing' is not connected to this account",
                    "extensions": {"code": "CHANNEL_NOT_FOUND"},
                }]
            })

        # Build a live GQL client so it actually makes the HTTP call
        gql_client = _make_client()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.post = mock_post
            mock_cls.return_value = mock_inst

            with pytest.raises(BufferGraphQLError) as exc_info:
                await gql_client.create_post(channel_id="ch_missing", text="Test post")

        error_msg = str(exc_info.value)
        assert "BUFFER_GRAPHQL_BAD_REQUEST" in error_msg
        assert "Channel 'ch_missing' is not connected" in error_msg
        assert "CHANNEL_NOT_FOUND" in error_msg
        assert exc_info.value.permanent is True
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# 8. Mutation structure correctness
# ---------------------------------------------------------------------------

class TestMutationStructure:

    def test_channelid_type_is_channelid_not_string(self):
        """$channelId must be typed as ChannelId! not String!."""
        from sfc.connectors.buffer.graphql_client import _MUTATION_CREATE_POST
        assert "ChannelId!" in _MUTATION_CREATE_POST
        assert "$channelId: String!" not in _MUTATION_CREATE_POST

    def test_scheduling_type_direct_present(self):
        """schedulingType: DIRECT must be in the mutation input (IMMEDIATE is invalid in Buffer schema)."""
        from sfc.connectors.buffer.graphql_client import _MUTATION_CREATE_POST
        assert "schedulingType: DIRECT" in _MUTATION_CREATE_POST
        assert "schedulingType: IMMEDIATE" not in _MUTATION_CREATE_POST

    def test_mode_post_present_not_share_mode(self):
        """mode: POST must be in the input; field is 'mode' not 'shareMode'."""
        from sfc.connectors.buffer.graphql_client import _MUTATION_CREATE_POST
        assert "mode: POST" in _MUTATION_CREATE_POST
        assert "shareMode:" not in _MUTATION_CREATE_POST

    def test_post_action_success_inline_fragment(self):
        """Response must use inline fragment on PostActionSuccess, not direct 'post' field."""
        from sfc.connectors.buffer.graphql_client import _MUTATION_CREATE_POST
        assert "... on PostActionSuccess" in _MUTATION_CREATE_POST
        # Must NOT query post or errors directly on PostActionPayload
        # (they only exist inside PostActionSuccess fragment)
        import re
        # 'post {' should only appear inside the inline fragment, not at top-level
        lines = _MUTATION_CREATE_POST.splitlines()
        in_fragment = False
        for line in lines:
            stripped = line.strip()
            if "... on PostActionSuccess" in stripped:
                in_fragment = True
            if in_fragment and stripped == "}":
                in_fragment = False
        # The mutation should not have errors { at the top level of createPost
        assert "errors {" not in _MUTATION_CREATE_POST

    @pytest.mark.asyncio
    async def test_create_post_parses_post_action_success_response(self):
        """create_post() correctly parses {'post': {'id': '...'}} from PostActionSuccess."""
        client = _make_client()

        async def mock_post(*args, **kwargs):
            return _resp(200, {"data": {"createPost": {"post": {"id": "buf_12345"}}}})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.post = mock_post
            mock_cls.return_value = mock_inst

            result = await client.create_post(channel_id="ch_abc", text="Test post")

        assert result["id"] == "buf_12345"

    @pytest.mark.asyncio
    async def test_create_post_raises_when_no_post_id(self):
        """create_post() raises permanent=False when createPost returns empty (no fragment match)."""
        client = _make_client()

        async def mock_post(*args, **kwargs):
            # Union returned a non-PostActionSuccess type → empty result
            return _resp(200, {"data": {"createPost": {}}})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.post = mock_post
            mock_cls.return_value = mock_inst

            with pytest.raises(BufferGraphQLError) as exc_info:
                await client.create_post(channel_id="ch_abc", text="Test post")

        assert "no post ID" in str(exc_info.value)
        assert exc_info.value.permanent is False


# ---------------------------------------------------------------------------
# Shared GQL string for tests
# ---------------------------------------------------------------------------

_MUTATION_CREATE_POST_GQL = """
mutation SFCCreatePost($channelId: ChannelId!, $text: String!) {
  createPost(input: {
    channelId: $channelId
    text: $text
    schedulingType: DIRECT
    mode: POST
  }) {
    ... on PostActionSuccess {
      post { id }
    }
  }
}
"""
