"""Buffer GraphQL API client — for Buffer API Keys (new API).

Buffer API Keys authenticate against the GraphQL endpoint, not the legacy REST API.
REST API (api.bufferapp.com/1) only accepts OAuth tokens; it rejects API Keys with
"Public API tokens are not accepted for REST API access".

Endpoint : https://api.buffer.com
Auth     : Authorization: Bearer <BUFFER_ACCESS_TOKEN>
Dry-run  : when LIVE_PUBLISHING_ENABLED=false, no network calls are made.

Channel type fields (current schema): id, name, displayName, service, avatar, isQueuePaused
NOTE: "handle" was removed from the Channel type. Use "name" (platform handle/username).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("sfc.connectors.buffer.graphql_client")

_BUFFER_GRAPHQL_URL = "https://api.buffer.com"
_DEFAULT_TIMEOUT = 30.0

# ---------------------------------------------------------------------------
# Auth-only query — validates token, returns user + org IDs (no channels).
# Channel type excluded here: fetching channels requires an organizationId.
# ---------------------------------------------------------------------------
_QUERY_WHOAMI = """
query SFCWhoAmI {
  account {
    id
    name
    email
    timezone
    organizations {
      id
      name
    }
  }
}
"""

# Channel discovery — requires organizationId from the account query above.
# Channel fields per current schema: id, name, displayName, service, avatar, isQueuePaused
# "handle" was removed from the Channel type; "name" carries the platform username.
_QUERY_GET_CHANNELS = """
query SFCGetChannels($organizationId: OrganizationId!) {
  channels(input: { organizationId: $organizationId }) {
    id
    name
    displayName
    service
    avatar
    isQueuePaused
  }
}
"""


class BufferGraphQLError(Exception):
    """Raised for confirmed Buffer GraphQL errors."""

    def __init__(self, message: str, status_code: int = 0, permanent: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.permanent = permanent


@dataclass
class BufferGraphQLUser:
    user_id: str
    name: str
    email: str
    timezone: str
    raw: dict[str, Any] = field(default_factory=dict)
    api_mode: str = "graphql"


@dataclass
class BufferGraphQLChannel:
    channel_id: str
    service: str
    name: str        # platform username / handle (Buffer schema field: name)
    display_name: str  # human-readable display name (Buffer schema field: displayName)
    avatar: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def handle(self) -> str:
        """Backwards-compat alias: returns name (the platform handle/username)."""
        return self.name

    @property
    def service_username(self) -> str:
        return self.name


class BufferGraphQLClient:
    """Async GraphQL client for the Buffer API (API Key authentication).

    Credentials come exclusively from BUFFER_ACCESS_TOKEN env var.
    Does not publish anything — validation queries are read-only.
    """

    def __init__(self) -> None:
        self._token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        self._url = os.environ.get("BUFFER_GRAPHQL_URL", _BUFFER_GRAPHQL_URL)
        self._timeout = float(os.environ.get("BUFFER_API_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT)))
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @staticmethod
    def is_api_key(token: str) -> bool:
        """Return True if the token looks like a Buffer API Key.

        Buffer API Keys contain hyphens (e.g., WB3L8sij...X1Rm).
        Legacy OAuth access tokens are alphanumeric without hyphens.
        """
        return bool(token) and "-" in token

    @property
    def has_token(self) -> bool:
        return bool(self._token)

    @property
    def is_live(self) -> bool:
        return self._live

    async def validate(self) -> BufferGraphQLUser | None:
        """Return user details if the token is accepted, or None on failure."""
        if not self._token:
            return None
        if not self._live:
            logger.info("[BufferGraphQL][DRY-RUN] Token validation skipped")
            return BufferGraphQLUser(
                user_id="dry_run",
                name="Dry Run User",
                email="",
                timezone="UTC",
                raw={"dry_run": True},
            )
        try:
            data = await self.query(_QUERY_WHOAMI)
            account = data.get("account", {})
            if not account:
                logger.warning("[BufferGraphQL] Validation query returned no account data")
                return None
            return BufferGraphQLUser(
                user_id=str(account.get("id", "")),
                name=account.get("name", ""),
                email=account.get("email", ""),
                timezone=account.get("timezone", "UTC"),
                raw=account,
            )
        except BufferGraphQLError as exc:
            logger.error("[BufferGraphQL] Validation failed: %s", exc)
            return None
        except Exception as exc:
            logger.error("[BufferGraphQL] Unexpected error during validation: %s", exc)
            return None

    async def get_channels(self) -> list[BufferGraphQLChannel]:
        """Return connected channels via org-scoped channels query.

        Flow: query account for org IDs → query channels per org.
        API Keys only work on the GraphQL endpoint (not REST).
        """
        if not self._token:
            return []
        if not self._live:
            logger.info("[BufferGraphQL][DRY-RUN] Channel discovery skipped")
            return []
        try:
            # Step 1: get organization IDs
            account_data = await self.query(_QUERY_WHOAMI)
            account = account_data.get("account", {})
            orgs = account.get("organizations", [])
            if not orgs:
                logger.info("[BufferGraphQL] No organizations found on account")
                return []

            # Step 2: get channels per org
            all_channels: list[BufferGraphQLChannel] = []
            seen_ids: set[str] = set()
            for org in orgs:
                org_id = org.get("id", "")
                if not org_id:
                    continue
                try:
                    ch_data = await self.query(_QUERY_GET_CHANNELS, {"organizationId": org_id})
                    for raw_ch in ch_data.get("channels", []):
                        ch_id = str(raw_ch.get("id", ""))
                        if ch_id and ch_id not in seen_ids:
                            seen_ids.add(ch_id)
                            all_channels.append(self._parse_channel(raw_ch))
                except Exception as exc:
                    logger.warning("[BufferGraphQL] Channel fetch failed for org %s: %s", org_id, exc)

            logger.info("[BufferGraphQL] Discovered %d channel(s) across %d org(s)", len(all_channels), len(orgs))
            return all_channels
        except Exception as exc:
            logger.error("[BufferGraphQL] Channel fetch failed: %s", exc)
            return []

    async def query(self, gql: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query and return the `data` payload."""
        if not self._live:
            return {"dry_run": True}
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {"query": gql}
        if variables:
            body["variables"] = variables
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(self._url, json=body, headers=headers)
            logger.debug("[BufferGraphQL] POST %s → %d", self._url, resp.status_code)
            return self._handle_response(resp)
        except httpx.TimeoutException as exc:
            raise BufferGraphQLError(f"Timeout: {exc}", permanent=False) from exc
        except httpx.RequestError as exc:
            raise BufferGraphQLError(f"Network error: {exc}", permanent=False) from exc

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_response(self, resp: httpx.Response) -> dict[str, Any]:
        if resp.status_code in (401, 403):
            msg = self._extract_error(resp)
            raise BufferGraphQLError(msg, status_code=resp.status_code, permanent=True)
        if resp.status_code >= 500:
            raise BufferGraphQLError(
                f"Buffer server error {resp.status_code}",
                status_code=resp.status_code,
                permanent=False,
            )
        if resp.status_code != 200:
            raise BufferGraphQLError(
                f"Unexpected HTTP {resp.status_code}",
                status_code=resp.status_code,
                permanent=False,
            )
        body = resp.json()
        errors = body.get("errors")
        if errors:
            messages = "; ".join(e.get("message", str(e)) for e in errors)
            # Treat auth errors as permanent
            permanent = any(
                "unauthorized" in e.get("message", "").lower()
                or "forbidden" in e.get("message", "").lower()
                for e in errors
            )
            raise BufferGraphQLError(messages, status_code=200, permanent=permanent)
        return body.get("data", body)

    def _extract_error(self, resp: httpx.Response) -> str:
        try:
            body = resp.json()
            return body.get("message", body.get("error", resp.text))
        except Exception:
            return resp.text or f"HTTP {resp.status_code}"

    def _parse_channel(self, raw: dict[str, Any]) -> BufferGraphQLChannel:
        # Buffer schema: "name" = platform handle/username, "displayName" = human-readable name
        name = raw.get("name", "")
        display_name = raw.get("displayName", name)
        return BufferGraphQLChannel(
            channel_id=str(raw.get("id", "")),
            service=raw.get("service", ""),
            name=name,
            display_name=display_name,
            avatar=raw.get("avatar", ""),
            raw=raw,
        )


_singleton: BufferGraphQLClient | None = None


def get_buffer_graphql_client() -> BufferGraphQLClient:
    global _singleton
    if _singleton is None:
        _singleton = BufferGraphQLClient()
    return _singleton
