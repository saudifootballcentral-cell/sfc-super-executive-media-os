"""Footage downloader — wraps yt-dlp for YouTube/remote URLs.

For local files (folder-watch assets), no download is performed.

Config:
    FOOTAGE_DOWNLOAD_DIR       — destination directory (default: artifacts/video/downloads)
    FOOTAGE_MAX_SIZE_MB        — abort if estimated file > N MB (default: 500)
    FOOTAGE_MAX_DURATION_SECS  — skip videos longer than N seconds (default: 600)
    FOOTAGE_DOWNLOAD_TIMEOUT   — yt-dlp subprocess timeout in seconds (default: 300)
    VIDEO_PROCESSING_ENABLED   — master switch; if false, downloads are skipped (dry-run path)
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from sfc.video_intelligence.discovery.models import DiscoveredAsset, DiscoveryStatus

logger = logging.getLogger("sfc.video_intelligence.discovery.downloader")


def _download_dir() -> Path:
    raw = os.environ.get("FOOTAGE_DOWNLOAD_DIR", "artifacts/video/downloads")
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _max_size_mb() -> float:
    try:
        return float(os.environ.get("FOOTAGE_MAX_SIZE_MB", "500"))
    except ValueError:
        return 500.0


def _max_duration_secs() -> float:
    try:
        return float(os.environ.get("FOOTAGE_MAX_DURATION_SECS", "600"))
    except ValueError:
        return 600.0


def _timeout() -> int:
    try:
        return int(os.environ.get("FOOTAGE_DOWNLOAD_TIMEOUT", "300"))
    except ValueError:
        return 300


def _processing_enabled() -> bool:
    return os.environ.get("VIDEO_PROCESSING_ENABLED", "false").lower() == "true"


class FootageDownloader:
    """Downloads remote footage via yt-dlp; passes through local files unchanged."""

    def __init__(self) -> None:
        self._download_dir = _download_dir()
        self._max_size_bytes = _max_size_mb() * 1024 * 1024
        self._max_duration = _max_duration_secs()
        self._timeout = _timeout()
        self._ytdlp_available = self._check_ytdlp()

    def _check_ytdlp(self) -> bool:
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def needs_download(self, asset: DiscoveredAsset) -> bool:
        """Return True if the asset requires a download step."""
        return bool(asset.url) and not bool(asset.local_path)

    def download(self, asset: DiscoveredAsset) -> DiscoveredAsset:
        """Download the asset's URL to local disk; mutates asset in place.

        If VIDEO_PROCESSING_ENABLED=false, skips download (dry-run mode).
        If the asset already has a local_path, returns it unchanged.
        """
        if not self.needs_download(asset):
            return asset

        if not _processing_enabled():
            logger.debug(
                "[Downloader] VIDEO_PROCESSING_ENABLED=false — skipping download: %s", asset.url
            )
            return asset

        if not self._ytdlp_available:
            logger.warning("[Downloader] yt-dlp not found — cannot download: %s", asset.url)
            asset.status = DiscoveryStatus.DOWNLOAD_FAILED
            return asset

        # Duration check via yt-dlp --get-duration (fast, no download)
        if self._max_duration > 0:
            duration = self._probe_duration(asset.url)
            if duration > 0:
                asset.metadata["probed_duration_seconds"] = duration
                if duration > self._max_duration:
                    logger.info(
                        "[Downloader] Skipping %s — duration %.0fs > limit %.0fs",
                        asset.url, duration, self._max_duration,
                    )
                    asset.status = DiscoveryStatus.SKIPPED_RIGHTS
                    return asset
                asset.duration_seconds = duration

        output_template = str(self._download_dir / "%(id)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--max-filesize", f"{int(self._max_size_bytes)}",
            "--output", output_template,
            "--print", "after_move:filepath",
            "--no-progress",
            "--quiet",
            asset.url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                logger.warning(
                    "[Downloader] yt-dlp failed (rc=%d) url=%s stderr=%s",
                    result.returncode, asset.url, result.stderr[:300],
                )
                asset.status = DiscoveryStatus.DOWNLOAD_FAILED
                return asset

            # Last non-empty line is the downloaded filepath
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if not lines:
                logger.warning("[Downloader] yt-dlp returned no filepath for %s", asset.url)
                asset.status = DiscoveryStatus.DOWNLOAD_FAILED
                return asset

            local_path = lines[-1]
            if not Path(local_path).exists():
                logger.warning(
                    "[Downloader] yt-dlp reported path does not exist: %s", local_path
                )
                asset.status = DiscoveryStatus.DOWNLOAD_FAILED
                return asset

            asset.local_path = local_path
            logger.info("[Downloader] Downloaded %s → %s", asset.url, local_path)

        except subprocess.TimeoutExpired:
            logger.warning("[Downloader] yt-dlp timed out after %ds for %s", self._timeout, asset.url)
            asset.status = DiscoveryStatus.DOWNLOAD_FAILED

        return asset

    def _probe_duration(self, url: str) -> float:
        """Use yt-dlp --get-duration to probe duration without downloading."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--get-duration", "--no-playlist", "--quiet", url],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return 0.0
            raw = result.stdout.strip()
            # Format: [[HH:]MM:]SS
            parts = raw.split(":")
            seconds = 0.0
            for part in parts:
                seconds = seconds * 60 + float(part)
            return seconds
        except Exception:
            return 0.0


_singleton: FootageDownloader | None = None


def get_footage_downloader() -> FootageDownloader:
    global _singleton
    if _singleton is None:
        _singleton = FootageDownloader()
    return _singleton
