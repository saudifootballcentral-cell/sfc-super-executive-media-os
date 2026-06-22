"""Buffer API rate-limit tracking and auto-throttle."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("sfc.connectors.buffer.rate_limits")

# Buffer publish API: 150 requests per 15-minute rolling window (conservative estimate)
_DEFAULT_WINDOW_SECONDS = 900
_DEFAULT_MAX_REQUESTS = 150


@dataclass
class RateLimitState:
    requests_made: int = 0
    remaining_quota: int = _DEFAULT_MAX_REQUESTS
    reset_time: float = field(default_factory=lambda: time.monotonic() + _DEFAULT_WINDOW_SECONDS)
    window_seconds: int = _DEFAULT_WINDOW_SECONDS
    max_requests: int = _DEFAULT_MAX_REQUESTS
    rate_limit_hits: int = 0


class BufferRateLimiter:
    """Tracks Buffer API quota and auto-throttles when near the limit.

    Thread-safe for single-process asyncio use.
    """

    def __init__(
        self,
        max_requests: int = _DEFAULT_MAX_REQUESTS,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._state = RateLimitState(
            max_requests=max_requests,
            remaining_quota=max_requests,
            window_seconds=window_seconds,
            reset_time=time.monotonic() + window_seconds,
        )
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a request slot is available, then consume one slot."""
        async with self._lock:
            self._maybe_reset_window()
            if self._state.remaining_quota <= 0:
                wait_secs = max(0.0, self._state.reset_time - time.monotonic())
                self._state.rate_limit_hits += 1
                logger.warning(
                    "[RateLimiter] Quota exhausted — waiting %.1fs for window reset", wait_secs
                )
                await asyncio.sleep(wait_secs)
                self._reset_window()

            self._state.requests_made += 1
            self._state.remaining_quota -= 1

    def record_429(self, retry_after_seconds: float = 60.0) -> None:
        """Called when the API returns 429; fast-forward reset time."""
        self._state.remaining_quota = 0
        self._state.reset_time = time.monotonic() + retry_after_seconds
        self._state.rate_limit_hits += 1
        logger.warning("[RateLimiter] 429 received — backing off %.1fs", retry_after_seconds)

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """Parse X-RateLimit-* headers if Buffer includes them."""
        remaining = headers.get("x-ratelimit-remaining")
        reset = headers.get("x-ratelimit-reset")
        if remaining is not None:
            try:
                self._state.remaining_quota = int(remaining)
            except ValueError:
                pass
        if reset is not None:
            try:
                self._state.reset_time = float(reset)
            except ValueError:
                pass

    @property
    def state(self) -> RateLimitState:
        return self._state

    @property
    def is_throttled(self) -> bool:
        self._maybe_reset_window()
        return self._state.remaining_quota <= 0

    def _maybe_reset_window(self) -> None:
        if time.monotonic() >= self._state.reset_time:
            self._reset_window()

    def _reset_window(self) -> None:
        self._state.remaining_quota = self._state.max_requests
        self._state.requests_made = 0
        self._state.reset_time = time.monotonic() + self._state.window_seconds
        logger.debug("[RateLimiter] Window reset — quota restored to %d", self._state.max_requests)


_singleton: BufferRateLimiter | None = None


def get_buffer_rate_limiter() -> BufferRateLimiter:
    global _singleton
    if _singleton is None:
        _singleton = BufferRateLimiter()
    return _singleton
