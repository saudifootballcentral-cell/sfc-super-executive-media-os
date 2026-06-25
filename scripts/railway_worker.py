"""Railway production worker — keeps the process alive and orchestrates the SFC pipeline.

Start command: python scripts/railway_worker.py

Startup sequence:
  1. Verify system binaries (ffmpeg, ffprobe)
  2. Verify core sfc imports
  3. Instantiate MasterOrchestrator (dry-run by default)
  4. Log startup success
  5. Enter heartbeat loop — logs alive every 60 seconds

Publishing is controlled exclusively by LIVE_PUBLISHING_ENABLED (default: false).
The worker never publishes anything unless that variable is explicitly set to "true".
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("sfc.railway_worker")

HEARTBEAT_INTERVAL = 60  # seconds


def _verify_system_binaries() -> None:
    missing = [b for b in ("ffmpeg", "ffprobe") if not shutil.which(b)]
    if missing:
        logger.error("FATAL: missing system binaries: %s — ensure ffmpeg is installed in the image", missing)
        sys.exit(1)
    logger.info("System binaries OK — ffmpeg=%s ffprobe=%s", shutil.which("ffmpeg"), shutil.which("ffprobe"))


def _verify_imports() -> None:
    try:
        import sfc  # noqa: F401
        from sfc.orchestration.master_orchestrator import MasterOrchestrator  # noqa: F401
        from sfc.connectors.buffer.api_client import BufferAPIClient  # noqa: F401
        from sfc.graph.graph import build_graph  # noqa: F401
        from sfc.video_intelligence.clipping.service import SmartClippingEngine  # noqa: F401
    except ImportError as exc:
        logger.error("FATAL: import failure — %s", exc)
        sys.exit(1)
    logger.info("Package imports OK — sfc v%s", sfc.__version__)


def _check_live_publishing() -> bool:
    live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
    if live:
        logger.warning(
            "LIVE_PUBLISHING_ENABLED=true — real content may be published to social platforms"
        )
    else:
        logger.info("LIVE_PUBLISHING_ENABLED=false — running in safe dry-run mode (default)")
    return live


def _log_env_diagnostics() -> None:
    """Log presence/state of key env vars without exposing secret values."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    buffer_token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    live_flag = os.environ.get("LIVE_PUBLISHING_ENABLED", "false")

    logger.info("--- Environment Diagnostics ---")
    logger.info("  ANTHROPIC_API_KEY present: %s", bool(anthropic_key))
    logger.info("  BUFFER_ACCESS_TOKEN present: %s", bool(buffer_token))
    logger.info("  LIVE_PUBLISHING_ENABLED: %s", live_flag)

    if buffer_token:
        from sfc.connectors.buffer.graphql_client import BufferGraphQLClient
        is_api_key = BufferGraphQLClient.is_api_key(buffer_token)
        masked = buffer_token[:6] + "..." + buffer_token[-4:]
        logger.info(
            "  BUFFER token type: %s (masked: %s)",
            "API Key (GraphQL)" if is_api_key else "OAuth token (REST)",
            masked,
        )
    else:
        logger.warning("  BUFFER token type: unknown — BUFFER_ACCESS_TOKEN not set")

    logger.info("--- End Environment Diagnostics ---")


async def _anthropic_health_check() -> None:
    """Verify Anthropic API key is present; attempt a minimal connectivity check."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        logger.warning("Anthropic health check: SKIPPED — ANTHROPIC_API_KEY not set")
        return
    try:
        import httpx
        # HEAD request to the Anthropic models endpoint — no tokens consumed, no generation
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            )
        if resp.status_code == 200:
            logger.info("Anthropic health check: OK (HTTP 200)")
        elif resp.status_code == 401:
            logger.error("Anthropic health check: FAILED — API key rejected (HTTP 401)")
        else:
            logger.warning("Anthropic health check: unexpected HTTP %d", resp.status_code)
    except Exception as exc:
        logger.warning("Anthropic health check: unreachable — %s", exc)


async def _startup() -> None:
    from sfc.orchestration.master_orchestrator import MasterOrchestrator

    logger.info("=== SFC Super Executive Media OS — Railway Worker Starting ===")

    _verify_system_binaries()
    _verify_imports()
    _log_env_diagnostics()
    live = _check_live_publishing()
    await _anthropic_health_check()

    orchestrator = MasterOrchestrator()
    logger.info("MasterOrchestrator instantiated — live_publishing=%s", live)
    logger.info("=== Startup complete — worker is running ===")

    return orchestrator


async def _heartbeat_loop(orchestrator: object) -> None:  # type: ignore[type-arg]
    start_time = time.monotonic()
    tick = 0
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        tick += 1
        uptime = int(time.monotonic() - start_time)
        logger.info("Heartbeat tick=%d uptime=%ds worker=alive", tick, uptime)


async def main() -> None:
    orchestrator = await _startup()
    await _heartbeat_loop(orchestrator)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by signal")
        sys.exit(0)
