"""Railway / Docker health check — validates runtime dependencies and core imports."""

from __future__ import annotations

import shutil
import sys


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(label: str) -> None:
    print(f"OK   {label}")


# System binaries
if not shutil.which("ffmpeg"):
    fail("ffmpeg binary not found — install ffmpeg in the production image")
ok("ffmpeg")

if not shutil.which("ffprobe"):
    fail("ffprobe binary not found — install ffmpeg (includes ffprobe) in the production image")
ok("ffprobe")

# Core graph
try:
    from sfc.graph.graph import build_graph
    build_graph()
    ok("graph")
except Exception as exc:
    fail(f"build_graph() raised: {exc}")

# Orchestrator
try:
    from sfc.orchestration.master_orchestrator import MasterOrchestrator
    ok("orchestrator")
except Exception as exc:
    fail(f"MasterOrchestrator import raised: {exc}")

# Buffer connector
try:
    from sfc.connectors.buffer.api_client import BufferAPIClient
    BufferAPIClient()
    ok("buffer_connector")
except Exception as exc:
    fail(f"BufferAPIClient raised: {exc}")

# Video Intelligence
try:
    from sfc.video_intelligence.clipping.service import SmartClippingEngine
    from sfc.video_intelligence.ingestion.service import VideoIngestionService
    from sfc.video_intelligence.rendering.service import get_video_rendering_service
    get_video_rendering_service()
    ok("video_intelligence")
except Exception as exc:
    fail(f"video_intelligence import raised: {exc}")

# Footage Discovery
try:
    from sfc.video_intelligence.discovery.service import get_footage_discovery_service
    get_footage_discovery_service()
    ok("footage_discovery")
except Exception as exc:
    fail(f"footage_discovery import raised: {exc}")

# Voiceover + Music
try:
    from sfc.video_intelligence.voiceover.service import get_voiceover_service
    from sfc.video_intelligence.music.service import get_music_library_service
    get_voiceover_service()
    get_music_library_service()
    ok("voiceover_music")
except Exception as exc:
    fail(f"voiceover/music import raised: {exc}")

# Platform publishers
try:
    from sfc.connectors.youtube.publisher import YouTubeVideoPublisher
    from sfc.connectors.instagram.publisher import InstagramReelPublisher
    ok("platform_publishers")
except Exception as exc:
    fail(f"platform_publishers import raised: {exc}")

print("healthy")
