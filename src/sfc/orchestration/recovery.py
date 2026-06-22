"""RecoveryEngine — retry, resume, rollback, and safe abort strategies."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Callable, Coroutine


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    ROLLBACK = "rollback"


class RecoveryResult:
    def __init__(self, strategy: RecoveryStrategy, success: bool, detail: str = "") -> None:
        self.strategy = strategy
        self.success = success
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "success": self.success,
            "detail": self.detail,
        }


class RecoveryEngine:
    """Applies a recovery strategy when a workflow stage fails.

    Default policy (override via constructor):
      - Attempt up to max_retries with exponential backoff
      - If retries exhausted: ABORT (safe default)
    """

    def __init__(self, max_retries: int = 2, base_backoff_seconds: float = 1.0) -> None:
        self.max_retries = max_retries
        self.base_backoff = base_backoff_seconds
        self._retry_counts: dict[str, int] = {}

    async def attempt_retry(
        self,
        stage_name: str,
        fn: Callable[[], Coroutine[Any, Any, Any]],
    ) -> RecoveryResult:
        """Retry `fn` up to max_retries times with exponential backoff."""
        count = self._retry_counts.get(stage_name, 0)
        if count >= self.max_retries:
            return RecoveryResult(
                strategy=RecoveryStrategy.ABORT,
                success=False,
                detail=f"Max retries ({self.max_retries}) exhausted for stage '{stage_name}'",
            )
        backoff = self.base_backoff * (2 ** count)
        await asyncio.sleep(backoff)
        self._retry_counts[stage_name] = count + 1
        try:
            await fn()
            return RecoveryResult(
                strategy=RecoveryStrategy.RETRY,
                success=True,
                detail=f"Succeeded on retry {count + 1}",
            )
        except Exception as exc:
            return RecoveryResult(
                strategy=RecoveryStrategy.RETRY,
                success=False,
                detail=f"Retry {count + 1} failed: {exc}",
            )

    def can_retry(self, stage_name: str) -> bool:
        return self._retry_counts.get(stage_name, 0) < self.max_retries

    def should_abort(self, stage_name: str, error: Exception) -> bool:
        """Heuristic: always abort on governance violations."""
        msg = str(error).lower()
        if "constitution" in msg or "governance" in msg or "approval" in msg:
            return True
        return not self.can_retry(stage_name)

    def reset_stage(self, stage_name: str) -> None:
        self._retry_counts.pop(stage_name, None)

    def retry_counts(self) -> dict[str, int]:
        return dict(self._retry_counts)
