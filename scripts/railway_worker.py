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

# Module-level proof — prints even if every subsequent import fails.
# This is the first thing that appears in Railway logs when the correct
# image is running; its absence means Railway built from a stale/wrong source.
print(f"[SFC-BOOT] railway_worker.py executing — file={__file__}", flush=True)
print(f"[SFC-BOOT] Python={sys.executable}  PYTHONPATH={os.environ.get('PYTHONPATH', '(not set)')}", flush=True)


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


def _log_import_diagnostics() -> None:
    """Print definitive runtime import proof to stdout (appears in Railway logs).

    This runs before any SFC business logic.  It answers the question:
    'Which code is Railway actually executing right now?'
    """
    import inspect
    import subprocess

    print("=" * 70, flush=True)
    print("SFC RUNTIME IMPORT DIAGNOSTICS", flush=True)
    print("=" * 70, flush=True)

    # --- Runtime environment ---
    print(f"  Python executable : {sys.executable}", flush=True)
    print(f"  Python version    : {sys.version}", flush=True)
    print(f"  cwd               : {os.getcwd()}", flush=True)
    print(f"  PYTHONPATH        : {os.environ.get('PYTHONPATH', '(not set)')}", flush=True)
    print(f"  SFC_REPO_ROOT     : {os.environ.get('SFC_REPO_ROOT', '(not set)')}", flush=True)
    print(f"  sys.path          : {sys.path}", flush=True)

    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        print(f"  git HEAD SHA      : {sha}", flush=True)
    except Exception:
        print("  git HEAD SHA      : unavailable", flush=True)

    print("", flush=True)

    # --- Import resolution ---
    try:
        import sfc
        print(f"  sfc.__file__               : {getattr(sfc, '__file__', None)}", flush=True)
        print(f"  sfc.__version__            : {getattr(sfc, '__version__', 'unknown')}", flush=True)
    except Exception as exc:
        print(f"  sfc import FAILED          : {exc}", flush=True)

    try:
        from sfc.ai.providers import claude as _claude_mod
        print(f"  claude.__file__            : {getattr(_claude_mod, '__file__', None)}", flush=True)
        has_sanitize = hasattr(_claude_mod, "_sanitize_payload")
        has_permanent = hasattr(_claude_mod, "_is_permanent_error")
        print(f"  _sanitize_payload exists   : {has_sanitize}", flush=True)
        print(f"  _is_permanent_error exists : {has_permanent}", flush=True)
        if has_sanitize:
            src_file = inspect.getsourcefile(_claude_mod._sanitize_payload)
            print(f"  _sanitize_payload source   : {src_file}", flush=True)
        else:
            print("  _sanitize_payload source   : MISSING — old code is running!", flush=True)
    except Exception as exc:
        print(f"  claude module FAILED       : {exc}", flush=True)

    try:
        from sfc.graph.nodes import super_executive as _se_mod
        print(f"  super_executive.__file__   : {getattr(_se_mod, '__file__', None)}", flush=True)
    except Exception as exc:
        print(f"  super_executive FAILED     : {exc}", flush=True)

    try:
        from sfc.tools import claude_client as _cc_mod
        print(f"  claude_client.__file__     : {getattr(_cc_mod, '__file__', None)}", flush=True)
    except Exception as exc:
        print(f"  claude_client FAILED       : {exc}", flush=True)

    print("", flush=True)

    # --- ExecutiveDecisionAI schema ---
    try:
        from sfc.ai.structured_output import ExecutiveDecisionAI
        fields = list(ExecutiveDecisionAI.model_fields.keys())
        required = [n for n, f in ExecutiveDecisionAI.model_fields.items() if f.is_required()]
        print(f"  ExecutiveDecisionAI.__module__    : {ExecutiveDecisionAI.__module__}", flush=True)
        print(f"  ExecutiveDecisionAI fields        : {fields}", flush=True)
        print(f"  ExecutiveDecisionAI required (=0) : {required}", flush=True)
        if required:
            print(f"  WARNING: {len(required)} required fields — validation will fail on partial responses!", flush=True)
    except Exception as exc:
        print(f"  ExecutiveDecisionAI FAILED        : {exc}", flush=True)

    print("", flush=True)

    # --- BreakingNewsCommandCenter ---
    try:
        from sfc.war_rooms.operations.breaking_news.service import BreakingNewsCommandCenter
        has_init = hasattr(BreakingNewsCommandCenter, "initialize")
        print(f"  BreakingNewsCommandCenter.initialize : {has_init}", flush=True)
        if not has_init:
            print("  WARNING: initialize() missing — war_room_router will raise AttributeError!", flush=True)
    except Exception as exc:
        print(f"  BreakingNewsCommandCenter FAILED     : {exc}", flush=True)

    # --- Prompt resolution ---
    try:
        from sfc.ai.prompt_loader import _find_repo_root
        repo_root = _find_repo_root()
        strategic_path = repo_root / "prompts" / "divisions" / "strategic_planning.md"
        print(f"  PromptLoader repo_root             : {repo_root}", flush=True)
        print(f"  strategic_planning.md exists       : {strategic_path.exists()}", flush=True)
        if not strategic_path.exists():
            print(f"  WARNING: prompt file missing at {strategic_path}", flush=True)
    except Exception as exc:
        print(f"  PromptLoader FAILED                : {exc}", flush=True)

    print("=" * 70, flush=True)
    print("END RUNTIME IMPORT DIAGNOSTICS", flush=True)
    print("=" * 70, flush=True)


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
    logger.info("=== SFC Super Executive Media OS — Railway Worker Starting ===")

    _verify_system_binaries()
    _verify_imports()
    _log_env_diagnostics()
    live = _check_live_publishing()
    await _anthropic_health_check()

    # Import only after _verify_imports() has confirmed the package is present.
    from sfc.orchestration.master_orchestrator import MasterOrchestrator
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
    # Diagnostics run before any SFC business logic — guaranteed to appear in
    # Railway logs regardless of whether downstream imports succeed or fail.
    _log_import_diagnostics()
    orchestrator = await _startup()
    await _heartbeat_loop(orchestrator)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by signal")
        sys.exit(0)
