"""RetryExecutor — exponential backoff retry for provider calls."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger("sfc.creative.providers.retry")


@dataclass
class RetryResult:
    success: bool
    result: Any = None
    error: str = ""
    attempts: int = 0


class RetryExecutor:
    """Retries an async callable with exponential backoff and per-call timeout."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._timeout = timeout_seconds

    async def execute(
        self,
        func: Callable[[], Awaitable[Any]],
        operation_name: str = "provider_call",
    ) -> RetryResult:
        """Run func() up to max_retries times.  Returns RetryResult."""
        last_error = ""
        for attempt in range(1, self._max_retries + 1):
            try:
                result = await asyncio.wait_for(func(), timeout=self._timeout)
                logger.debug(
                    "[Retry] Success | op=%s attempt=%d", operation_name, attempt
                )
                return RetryResult(success=True, result=result, attempts=attempt)
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self._timeout}s on attempt {attempt}"
                logger.warning(
                    "[Retry] Timeout | op=%s attempt=%d/%d",
                    operation_name,
                    attempt,
                    self._max_retries,
                )
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "[Retry] Failed | op=%s attempt=%d/%d error=%s",
                    operation_name,
                    attempt,
                    self._max_retries,
                    exc,
                )

            if attempt < self._max_retries:
                delay = self._base_delay * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

        return RetryResult(
            success=False,
            error=last_error,
            attempts=self._max_retries,
        )
