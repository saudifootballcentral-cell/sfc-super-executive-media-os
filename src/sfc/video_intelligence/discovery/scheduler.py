"""Footage Discovery Scheduler — runs discovery cycles on a configurable interval.

Mirrors the AutonomousScheduler pattern exactly.

Config:
    FOOTAGE_DISCOVERY_ENABLED            — master switch (default: false)
    FOOTAGE_DISCOVERY_INTERVAL_MINUTES   — cycle interval (default: 15)
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger("sfc.video_intelligence.discovery.scheduler")


def _is_enabled() -> bool:
    return os.environ.get("FOOTAGE_DISCOVERY_ENABLED", "false").lower() == "true"


def _interval_seconds() -> float:
    try:
        minutes = float(os.environ.get("FOOTAGE_DISCOVERY_INTERVAL_MINUTES", "15"))
        return max(minutes * 60.0, 60.0)  # minimum 1 minute
    except ValueError:
        return 900.0


class FootageDiscoveryScheduler:
    """Periodically runs FootageDiscoveryService.run_cycle() as an asyncio task."""

    async def run(self) -> None:
        if not _is_enabled():
            logger.info(
                "[FootageDiscoveryScheduler] FOOTAGE_DISCOVERY_ENABLED=false — scheduler idle "
                "(set to 'true' and configure provider env vars to activate)"
            )
            return

        interval = _interval_seconds()
        logger.info(
            "[FootageDiscoveryScheduler] Starting — interval=%.0fs", interval
        )

        from sfc.video_intelligence.discovery.service import get_footage_discovery_service
        service = get_footage_discovery_service()

        while True:
            try:
                run = await service.run_cycle()
                logger.info(
                    "[FootageDiscoveryScheduler] Cycle complete — "
                    "discovered=%d submitted=%d failed=%d duration=%.1fs",
                    run.discovered,
                    run.submitted,
                    run.failed,
                    run.duration_seconds,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "[FootageDiscoveryScheduler] Cycle error: %s", exc, exc_info=True
                )

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("[FootageDiscoveryScheduler] Cancelled — exiting cleanly")
                raise
