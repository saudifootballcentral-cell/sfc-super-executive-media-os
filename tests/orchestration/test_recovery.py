"""Tests for RecoveryEngine — Package 10D."""

from __future__ import annotations

import pytest

from sfc.orchestration.recovery import RecoveryEngine, RecoveryStrategy


class TestRecoveryEngine:
    def setup_method(self):
        self.engine = RecoveryEngine(max_retries=2, base_backoff_seconds=0.01)

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        call_count = [0]

        async def flaky():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("flaky failure")

        # First attempt fails; second attempt succeeds
        r1 = await self.engine.attempt_retry("stage", flaky)
        assert r1.success is False
        r2 = await self.engine.attempt_retry("stage", flaky)
        assert r2.success is True
        assert r2.strategy == RecoveryStrategy.RETRY

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_retries(self):
        async def always_fail():
            raise RuntimeError("permanent failure")

        # Exhaust retries
        for _ in range(self.engine.max_retries):
            await self.engine.attempt_retry("stage", always_fail)

        result = await self.engine.attempt_retry("stage", always_fail)
        assert result.success is False
        assert result.strategy == RecoveryStrategy.ABORT

    def test_can_retry_initially_true(self):
        assert self.engine.can_retry("new_stage") is True

    def test_can_retry_false_after_exhaustion(self):
        self.engine._retry_counts["my_stage"] = 2
        assert self.engine.can_retry("my_stage") is False

    def test_should_abort_on_governance_error(self):
        err = RuntimeError("governance violation")
        assert self.engine.should_abort("stage", err) is True

    def test_should_abort_on_constitution_error(self):
        err = RuntimeError("constitution breach")
        assert self.engine.should_abort("stage", err) is True

    def test_should_not_abort_on_regular_error_with_retries(self):
        err = RuntimeError("timeout")
        assert self.engine.should_abort("new_stage", err) is False

    def test_reset_stage_clears_count(self):
        self.engine._retry_counts["s"] = 2
        self.engine.reset_stage("s")
        assert self.engine.can_retry("s") is True

    def test_retry_counts_dict(self):
        self.engine._retry_counts["a"] = 1
        self.engine._retry_counts["b"] = 2
        counts = self.engine.retry_counts()
        assert counts["a"] == 1
        assert counts["b"] == 2
