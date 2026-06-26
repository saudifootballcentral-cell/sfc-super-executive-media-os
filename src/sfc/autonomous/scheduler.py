"""AutonomousScheduler — wraps AutonomousLoop in an asyncio scan loop.

Required Railway Variables:
  AUTONOMOUS_ENABLED               — set to "true" to activate (default: false)
  AUTONOMOUS_SCAN_INTERVAL_MINUTES — scan interval in minutes (default: 30)

Also read (but not required here — enforced by publisher/loop):
  LIVE_PUBLISHING_ENABLED          — must be "true" for real Buffer posts
  OPERATOR_AUTO_APPROVE            — must be "true" for autonomous publishing
  DEDUP_WINDOW_HOURS               — dedup TTL hours (default: 24)
"""

from __future__ import annotations

import asyncio
import logging
import os

from sfc.autonomous.dedup_store import DedupStore
from sfc.autonomous.loop import AutonomousLoop
from sfc.autonomous.metrics import LoopMetrics
from sfc.autonomous.source_provider import FixtureSourceProvider

logger = logging.getLogger("sfc.autonomous.scheduler")

_DEFAULT_SCAN_INTERVAL_MINUTES = 30.0


class AutonomousScheduler:
    """Runs AutonomousLoop on a configurable interval as an asyncio Task.

    Designed to run concurrently alongside the Railway heartbeat loop.
    If AUTONOMOUS_ENABLED=false (default), run() exits immediately.
    """

    def __init__(self) -> None:
        self._enabled = os.environ.get("AUTONOMOUS_ENABLED", "false").lower() == "true"
        self._interval_minutes = float(
            os.environ.get("AUTONOMOUS_SCAN_INTERVAL_MINUTES", str(_DEFAULT_SCAN_INTERVAL_MINUTES))
        )
        self._metrics = LoopMetrics()
        self._loop_instance: AutonomousLoop | None = None

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def metrics(self) -> LoopMetrics:
        return self._metrics

    def _build_loop(self) -> AutonomousLoop:
        from sfc.orchestration.master_orchestrator import MasterOrchestrator
        return AutonomousLoop(
            orchestrator=MasterOrchestrator(),
            source_provider=FixtureSourceProvider(),
            dedup_store=DedupStore(),
            metrics=self._metrics,
        )

    async def run(self) -> None:
        """Main scheduler loop — runs until the asyncio Task is cancelled."""
        if not self._enabled:
            logger.info(
                "[Scheduler] AUTONOMOUS_ENABLED=false — autonomous loop disabled, scheduler idle"
            )
            return

        interval_seconds = self._interval_minutes * 60.0
        live_flag = os.environ.get("LIVE_PUBLISHING_ENABLED", "false")
        auto_flag = os.environ.get("OPERATOR_AUTO_APPROVE", "false")

        logger.info(
            "[Scheduler] Starting — interval=%.0fmin LIVE_PUBLISHING_ENABLED=%s OPERATOR_AUTO_APPROVE=%s",
            self._interval_minutes, live_flag, auto_flag,
        )

        self._loop_instance = self._build_loop()

        while True:
            try:
                result = await self._loop_instance.run_cycle()
                logger.info(
                    "[Scheduler] Cycle result — status=%s governance=%s published=%s metrics=%s",
                    result.get("status"),
                    result.get("governance_approved"),
                    result.get("published"),
                    self._metrics.to_dict(),
                )
            except asyncio.CancelledError:
                logger.info("[Scheduler] Task cancelled — shutting down gracefully")
                raise
            except Exception as exc:
                logger.error("[Scheduler] Unhandled exception in scheduler run loop: %s", exc, exc_info=True)

            logger.info("[Scheduler] Sleeping %.0fs until next scan", interval_seconds)
            await asyncio.sleep(interval_seconds)
