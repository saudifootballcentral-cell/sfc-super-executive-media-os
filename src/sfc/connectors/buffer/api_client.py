"""Buffer API v1 HTTP client — all credentials from environment variables only."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("sfc.connectors.buffer.api_client")

_BUFFER_API_BASE = "https://api.bufferapp.com/1"
_DEFAULT_TIMEOUT = 30.0


class BufferAPIError(Exception):
    """Raised for confirmed Buffer API errors."""

    def __init__(self, message: str, status_code: int = 0, permanent: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.permanent = permanent


class BufferAPIClient:
    """Thin async HTTP wrapper around the Buffer API v1.

    When LIVE_PUBLISHING_ENABLED=false (default), every method returns a
    dry-run response dict without making any network calls.
    """

    def __init__(self) -> None:
        # Credentials loaded from env — never hardcoded
        self._token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        self._base_url = os.environ.get("BUFFER_API_BASE_URL", _BUFFER_API_BASE)
        self._timeout = float(os.environ.get("BUFFER_API_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT)))
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._live:
            return self._dry_run_response("GET", path, params or {})
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._live:
            return self._dry_run_response("POST", path, data or {})
        return await self._request("POST", path, data=data)

    async def delete(self, path: str) -> dict[str, Any]:
        if not self._live:
            return self._dry_run_response("DELETE", path, {})
        return await self._request("DELETE", path)

    @property
    def is_live(self) -> bool:
        return self._live

    @property
    def has_token(self) -> bool:
        return bool(self._token)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        params = kwargs.pop("params", None) or {}
        data = kwargs.pop("data", None)

        # Always pass token
        params["access_token"] = self._token

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                if method == "GET":
                    resp = await client.get(url, params=params)
                elif method == "POST":
                    form = dict(params)
                    if data:
                        form.update(data)
                    resp = await client.post(url, data=form)
                elif method == "DELETE":
                    resp = await client.delete(url, params=params)
                else:
                    raise BufferAPIError(f"Unsupported method: {method}")

            logger.debug("[BufferAPI] %s %s → %d", method, path, resp.status_code)
            return self._handle_response(resp)

        except httpx.TimeoutException as exc:
            raise BufferAPIError(f"Timeout calling {path}: {exc}", permanent=False) from exc
        except httpx.RequestError as exc:
            raise BufferAPIError(f"Network error calling {path}: {exc}", permanent=False) from exc

    def _handle_response(self, resp: httpx.Response) -> dict[str, Any]:
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            raise BufferAPIError("Rate limit exceeded", status_code=429, permanent=False)
        if resp.status_code in (400, 401, 403):
            msg = self._extract_error(resp)
            raise BufferAPIError(msg, status_code=resp.status_code, permanent=True)
        if resp.status_code >= 500:
            raise BufferAPIError(f"Buffer server error {resp.status_code}", status_code=resp.status_code, permanent=False)
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        raise BufferAPIError(f"Unexpected status {resp.status_code}", status_code=resp.status_code, permanent=False)

    def _extract_error(self, resp: httpx.Response) -> str:
        try:
            body = resp.json()
            return body.get("error", body.get("message", resp.text))
        except Exception:
            return resp.text or f"HTTP {resp.status_code}"

    def _dry_run_response(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        logger.debug("[BufferAPI][DRY-RUN] %s %s payload_keys=%s", method, path, list(payload.keys()))
        return {
            "dry_run": True,
            "method": method,
            "path": path,
            "success": True,
            "id": f"dry_run_{path.replace('/', '_')}",
        }


_singleton: BufferAPIClient | None = None


def get_buffer_api_client() -> BufferAPIClient:
    global _singleton
    if _singleton is None:
        _singleton = BufferAPIClient()
    return _singleton
