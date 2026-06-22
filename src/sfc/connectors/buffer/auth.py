"""Buffer authentication — validate token, introspect user, health check."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from sfc.connectors.buffer.api_client import BufferAPIClient, get_buffer_api_client

logger = logging.getLogger("sfc.connectors.buffer.auth")


@dataclass
class BufferUser:
    user_id: str
    name: str
    email: str
    plan: str
    timezone: str
    raw: dict[str, Any]


class BufferAuth:
    """Manages Buffer authentication state.

    Credentials come exclusively from BUFFER_ACCESS_TOKEN env var.
    """

    def __init__(self, client: BufferAPIClient | None = None) -> None:
        self._client = client or get_buffer_api_client()
        self._token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        self._user: BufferUser | None = None
        self._validated = False

    async def validate_token(self) -> bool:
        """Return True if the current token is accepted by Buffer."""
        if not self._token:
            logger.warning("[BufferAuth] No BUFFER_ACCESS_TOKEN set")
            return False
        try:
            data = await self._client.get("user.json")
            if data.get("dry_run"):
                logger.info("[BufferAuth][DRY-RUN] Token validation skipped")
                self._validated = True
                return True
            self._user = self._parse_user(data)
            self._validated = True
            logger.info("[BufferAuth] Token valid — user=%s", self._user.name)
            return True
        except Exception as exc:
            logger.error("[BufferAuth] Token validation failed: %s", exc)
            self._validated = False
            return False

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
            "user_id": self._user.user_id if self._user else None,
            "plan": self._user.plan if self._user else None,
        }

    @property
    def is_authenticated(self) -> bool:
        return bool(self._token) and self._validated

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _parse_user(self, data: dict[str, Any]) -> BufferUser:
        return BufferUser(
            user_id=str(data.get("_id", data.get("id", ""))),
            name=data.get("name", ""),
            email=data.get("email", ""),
            plan=data.get("plan", ""),
            timezone=data.get("timezone", "UTC"),
            raw=data,
        )


_singleton: BufferAuth | None = None


def get_buffer_auth() -> BufferAuth:
    global _singleton
    if _singleton is None:
        _singleton = BufferAuth()
    return _singleton
