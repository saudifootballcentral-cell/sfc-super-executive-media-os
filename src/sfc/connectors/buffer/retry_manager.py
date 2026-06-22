"""Exponential-backoff retry engine for Buffer API calls."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

from sfc.connectors.buffer.api_client import BufferAPIError

logger = logging.getLogger("sfc.connectors.buffer.retry_manager")

T = TypeVar("T")

# Retry schedule per spec: 1min → 2min → 4min → 8min → 16min
_DEFAULT_DELAYS_SECONDS = [60, 120, 240, 480, 960]


@dataclass
class RetryRecord:
    attempt: int = 0
    last_error: str = ""
    delay_seconds: float = 0.0
    exhausted: bool = False
    succeeded: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)


class BufferRetryManager:
    """Manages per-post retry state with configurable exponential backoff.

    Permanent errors (400/401/403) are never retried.
    Transient errors (429/5xx/timeout/network) retry up to len(delays) times.
    """

    def __init__(self, delays_seconds: list[int] | None = None) -> None:
        self._delays = delays_seconds if delays_seconds is not None else list(_DEFAULT_DELAYS_SECONDS)
        self._records: dict[str, RetryRecord] = {}

    async def call_with_retry(
        self,
        key: str,
        fn: Callable[[], Awaitable[T]],
        *,
        skip_wait: bool = False,  # set True in tests to skip actual sleep
    ) -> T:
        """Execute fn with automatic retry on transient failure.

        Args:
            key: Unique key for this operation (post_id or similar).
            fn: Async callable to invoke.
            skip_wait: Skip actual asyncio.sleep (for tests).

        Returns:
            Result of fn on success.

        Raises:
            BufferAPIError: When retries are exhausted or error is permanent.
        """
        record = self._records.setdefault(key, RetryRecord())

        while True:
            try:
                result = await fn()
                record.succeeded = True
                record.history.append({"attempt": record.attempt, "outcome": "success"})
                logger.debug("[Retry] %s succeeded on attempt %d", key, record.attempt)
                return result

            except BufferAPIError as exc:
                record.last_error = str(exc)
                record.history.append({"attempt": record.attempt, "error": str(exc), "permanent": exc.permanent})

                if exc.permanent:
                    record.exhausted = True
                    logger.error("[Retry] %s permanent failure (status=%d): %s", key, exc.status_code, exc)
                    raise

                if record.attempt >= len(self._delays):
                    record.exhausted = True
                    logger.error("[Retry] %s exhausted after %d attempts: %s", key, record.attempt, exc)
                    raise

                delay = self._delays[record.attempt]
                record.delay_seconds = delay
                record.attempt += 1
                logger.warning(
                    "[Retry] %s transient error (status=%d) — retry %d/%d in %ds",
                    key, exc.status_code, record.attempt, len(self._delays), delay,
                )
                if not skip_wait:
                    await asyncio.sleep(delay)

    def get_record(self, key: str) -> RetryRecord | None:
        return self._records.get(key)

    def reset(self, key: str) -> None:
        self._records.pop(key, None)

    def clear(self) -> None:
        self._records.clear()


_singleton: BufferRetryManager | None = None


def get_buffer_retry_manager() -> BufferRetryManager:
    global _singleton
    if _singleton is None:
        _singleton = BufferRetryManager()
    return _singleton
