"""Buffer authentication — validate token, introspect user, health check.

Token routing:
  Buffer API Keys (contain hyphens) → try GraphQL endpoint first
  Legacy OAuth tokens (no hyphens) → REST endpoint only
  Either type falls back gracefully if the primary path fails.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from sfc.connectors.buffer.api_client import BufferAPIClient, get_buffer_api_client
from sfc.connectors.buffer.graphql_client import (
    BufferGraphQLClient,
    BufferGraphQLUser,
    get_buffer_graphql_client,
)

logger = logging.getLogger("sfc.connectors.buffer.auth")


@dataclass
class BufferUser:
    user_id: str
    name: str
    email: str
    plan: str
    timezone: str
    raw: dict[str, Any]
    api_mode: str = "rest"  # "graphql" | "rest" | "dry_run"


class BufferAuth:
    """Manages Buffer authentication state.

    Credentials come exclusively from BUFFER_ACCESS_TOKEN env var.

    Validation strategy:
      1. If token looks like a Buffer API Key (contains '-'), try GraphQL first.
      2. On GraphQL failure, fall back to REST.
      3. Legacy OAuth tokens go directly to REST.
    """

    def __init__(
        self,
        client: BufferAPIClient | None = None,
        graphql_client: BufferGraphQLClient | None = None,
    ) -> None:
        self._client = client or get_buffer_api_client()
        self._gql = graphql_client or get_buffer_graphql_client()
        self._token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        self._user: BufferUser | None = None
        self._validated = False

    async def validate_token(self) -> bool:
        """Return True if the current token is accepted by Buffer.

        Tries GraphQL first for API Keys, REST for OAuth tokens.
        Falls back to the other path if the primary attempt fails.
        """
        if not self._token:
            logger.warning("[BufferAuth] No BUFFER_ACCESS_TOKEN set")
            return False

        # Dry-run shortcut — no network calls
        if not self._client.is_live:
            logger.info("[BufferAuth][DRY-RUN] Token validation skipped")
            self._user = BufferUser(
                user_id="dry_run",
                name="Dry Run",
                email="",
                plan="",
                timezone="UTC",
                raw={"dry_run": True},
                api_mode="dry_run",
            )
            self._validated = True
            return True

        # Choose primary path based on token shape
        if BufferGraphQLClient.is_api_key(self._token):
            ok = await self._validate_via_graphql()
            if ok:
                return True
            logger.info("[BufferAuth] GraphQL validation failed; falling back to REST")
            return await self._validate_via_rest()
        else:
            ok = await self._validate_via_rest()
            if ok:
                return True
            logger.info("[BufferAuth] REST validation failed; trying GraphQL fallback")
            return await self._validate_via_graphql()

    async def get_user(self) -> BufferUser | None:
        """Return authenticated user, fetching if not yet cached."""
        if self._user is None:
            await self.validate_token()
        return self._user

    async def health_check(self) -> dict[str, Any]:
        """Return auth health status."""
        if not self._token:
            return {"ok": False, "reason": "no_token", "live": self._client.is_live}
        if not self._validated:
            ok = await self.validate_token()
        else:
            ok = True
        return {
            "ok": ok,
            "live": self._client.is_live,
            "has_token": bool(self._token),
            "api_mode": self._user.api_mode if self._user else "unknown",
            "is_api_key": BufferGraphQLClient.is_api_key(self._token),
            "user_id": self._user.user_id if self._user else None,
            "plan": self._user.plan if self._user else None,
        }

    @property
    def is_authenticated(self) -> bool:
        return bool(self._token) and self._validated

    @property
    def api_mode(self) -> str:
        """Return 'graphql', 'rest', 'dry_run', or 'unknown'."""
        return self._user.api_mode if self._user else "unknown"

    # ------------------------------------------------------------------
    # Internal — GraphQL path
    # ------------------------------------------------------------------

    async def _validate_via_graphql(self) -> bool:
        try:
            gql_user = await self._gql.validate()
            if gql_user is None:
                return False
            self._user = self._gql_user_to_buffer_user(gql_user)
            self._validated = True
            logger.info("[BufferAuth] Token valid via GraphQL — user=%s", self._user.name)
            return True
        except Exception as exc:
            logger.warning("[BufferAuth] GraphQL validation error: %s", exc)
            return False

    def _gql_user_to_buffer_user(self, gql_user: BufferGraphQLUser) -> BufferUser:
        return BufferUser(
            user_id=gql_user.user_id,
            name=gql_user.name,
            email=gql_user.email,
            plan=gql_user.raw.get("plan", ""),
            timezone=gql_user.timezone,
            raw=gql_user.raw,
            api_mode=gql_user.api_mode,
        )

    # ------------------------------------------------------------------
    # Internal — REST path (legacy OAuth)
    # ------------------------------------------------------------------

    async def _validate_via_rest(self) -> bool:
        try:
            data = await self._client.get("user.json")
            if data.get("dry_run"):
                logger.info("[BufferAuth][DRY-RUN] REST token validation skipped")
                self._user = BufferUser(
                    user_id="dry_run",
                    name="Dry Run",
                    email="",
                    plan="",
                    timezone="UTC",
                    raw={"dry_run": True},
                    api_mode="dry_run",
                )
                self._validated = True
                return True
            self._user = self._parse_rest_user(data)
            self._validated = True
            logger.info("[BufferAuth] Token valid via REST — user=%s", self._user.name)
            return True
        except Exception as exc:
            logger.error("[BufferAuth] REST token validation failed: %s", exc)
            self._validated = False
            return False

    def _parse_rest_user(self, data: dict[str, Any]) -> BufferUser:
        return BufferUser(
            user_id=str(data.get("_id", data.get("id", ""))),
            name=data.get("name", ""),
            email=data.get("email", ""),
            plan=data.get("plan", ""),
            timezone=data.get("timezone", "UTC"),
            raw=data,
            api_mode="rest",
        )


_singleton: BufferAuth | None = None


def get_buffer_auth() -> BufferAuth:
    global _singleton
    if _singleton is None:
        _singleton = BufferAuth()
    return _singleton
