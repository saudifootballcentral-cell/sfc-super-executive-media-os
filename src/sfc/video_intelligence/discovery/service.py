"""Footage Discovery Service — orchestrates all providers, dedup, download, and submission.

The service runs one discovery cycle:
  1. Ask each enabled provider to discover assets
  2. Deduplicate by URL / local_path against a TTL store
  3. Download remote assets (via FootageDownloader / yt-dlp)
  4. Submit downloadable assets to VideoIntelligenceOrchestrator as VideoSource objects
  5. Return a DiscoveryRun summary

Config:
    FOOTAGE_DEDUP_WINDOW_HOURS  — dedup TTL in hours (default: 48)
    VIDEO_PROCESSING_ENABLED    — master switch; when false, assets are discovered &
                                  deduplicated but skipped at the submission step
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from sfc.video_intelligence.discovery.downloader import get_footage_downloader
from sfc.video_intelligence.discovery.models import (
    DiscoveredAsset,
    DiscoveryRun,
    DiscoveryStatus,
)
from sfc.video_intelligence.discovery.providers.base import FootageProvider
from sfc.video_intelligence.discovery.providers.direct_url import DirectUrlProvider
from sfc.video_intelligence.discovery.providers.folder_watch import FolderWatchProvider
from sfc.video_intelligence.discovery.providers.rss_media import RssMediaFeedProvider
from sfc.video_intelligence.discovery.providers.youtube import YouTubeChannelProvider

logger = logging.getLogger("sfc.video_intelligence.discovery.service")


def _dedup_window() -> float:
    try:
        return float(os.environ.get("FOOTAGE_DEDUP_WINDOW_HOURS", "48"))
    except ValueError:
        return 48.0


def _processing_enabled() -> bool:
    return os.environ.get("VIDEO_PROCESSING_ENABLED", "false").lower() == "true"


class _FootageDedupStore:
    """Simple in-memory URL dedup store (mirrors DedupStore pattern)."""

    import hashlib
    import time

    def __init__(self, window_hours: float) -> None:
        self._window_secs = window_hours * 3600.0
        self._store: dict[str, float] = {}

    def _fp(self, key: str) -> str:
        import hashlib
        return hashlib.sha256(f"footage:{key.strip().lower().rstrip('/')}".encode()).hexdigest()

    def is_seen(self, key: str) -> bool:
        self._evict()
        return self._fp(key) in self._store

    def mark_seen(self, key: str) -> None:
        import time
        self._store[self._fp(key)] = time.monotonic() + self._window_secs

    def _evict(self) -> None:
        import time
        now = time.monotonic()
        for k in list(self._store):
            if self._store[k] <= now:
                del self._store[k]


class FootageDiscoveryService:
    """Runs one footage discovery cycle across all registered providers."""

    def __init__(self) -> None:
        self._providers: list[FootageProvider] = [
            YouTubeChannelProvider(),
            RssMediaFeedProvider(),
            FolderWatchProvider(),
            DirectUrlProvider(),
        ]
        self._dedup = _FootageDedupStore(window_hours=_dedup_window())
        self._downloader = get_footage_downloader()

    def register_provider(self, provider: FootageProvider) -> None:
        self._providers.append(provider)
        logger.info("[DiscoveryService] Registered provider: %s", provider.name)

    async def run_cycle(self) -> DiscoveryRun:
        run = DiscoveryRun()
        logger.info("[DiscoveryService] Starting discovery cycle run_id=%s", run.run_id)

        for provider in self._providers:
            if not provider.is_enabled:
                continue
            try:
                assets = await provider.discover()
                run.discovered += len(assets)
                for asset in assets:
                    await self._process_asset(asset, run)
            except Exception as exc:
                msg = f"Provider {provider.name} failed: {exc}"
                logger.warning("[DiscoveryService] %s", msg)
                run.errors.append(msg)

        run.completed_at = datetime.utcnow()
        logger.info(
            "[DiscoveryService] Cycle complete run_id=%s discovered=%d "
            "deduped=%d downloaded=%d submitted=%d failed=%d",
            run.run_id,
            run.discovered,
            run.deduplicated,
            run.downloaded,
            run.submitted,
            run.failed,
        )
        return run

    async def _process_asset(self, asset: DiscoveredAsset, run: DiscoveryRun) -> None:
        # Dedup
        dedup_key = asset.dedup_key
        if not dedup_key:
            logger.debug("[DiscoveryService] Asset has no URL or path — skipping")
            run.failed += 1
            return

        if self._dedup.is_seen(dedup_key):
            asset.status = DiscoveryStatus.SKIPPED_DEDUP
            run.deduplicated += 1
            logger.debug("[DiscoveryService] Dedup hit: %s", dedup_key)
            return

        self._dedup.mark_seen(dedup_key)

        # Rights check — restricted assets are never downloaded or submitted
        if asset.rights_status == "restricted":
            asset.status = DiscoveryStatus.SKIPPED_RIGHTS
            run.deduplicated += 1
            logger.info("[DiscoveryService] Rights blocked: %s", dedup_key)
            return

        # Download (only for remote URLs with no local_path)
        if self._downloader.needs_download(asset):
            self._downloader.download(asset)
            if asset.status == DiscoveryStatus.DOWNLOAD_FAILED:
                run.failed += 1
                run.assets.append(asset)
                return
            run.downloaded += 1

        # Submit to Video Intelligence pipeline
        submitted = await self._submit(asset)
        if submitted:
            asset.status = DiscoveryStatus.SUBMITTED
            run.submitted += 1
        else:
            asset.status = DiscoveryStatus.PIPELINE_FAILED
            run.failed += 1

        run.assets.append(asset)

    async def _submit(self, asset: DiscoveredAsset) -> bool:
        """Convert DiscoveredAsset → VideoSource and submit to orchestrator."""
        if not _processing_enabled():
            logger.debug(
                "[DiscoveryService] VIDEO_PROCESSING_ENABLED=false — skipping submission: %s",
                asset.dedup_key,
            )
            return True  # count as submitted (will be a dry-run inside orchestrator)

        try:
            from sfc.video_intelligence.ingestion.models import (
                RightsStatus,
                VideoSource,
                VideoSourceType,
            )
            from sfc.video_intelligence.orchestrator import get_video_intelligence_orchestrator

            orchestrator = get_video_intelligence_orchestrator()

            # Map rights_status string → RightsStatus enum
            rights_map = {e.value: e for e in RightsStatus}
            rights = rights_map.get(asset.rights_status, RightsStatus.UNKNOWN)

            # Map source_type string → VideoSourceType enum
            source_type_map = {e.value: e for e in VideoSourceType}
            source_type = source_type_map.get(asset.source_type, VideoSourceType.YOUTUBE_URL)

            source = VideoSource(
                title=asset.title,
                url=asset.url,
                path=asset.local_path,
                source_type=source_type,
                rights_status=rights,
                submitter="footage_discovery",
                metadata={
                    **asset.metadata,
                    "discovery_asset_id": asset.asset_id,
                    "provider_name": asset.provider_name,
                    "description": asset.description,
                    "duration_seconds": asset.duration_seconds,
                    "channel_name": asset.channel_name,
                    "channel_id": asset.channel_id,
                    "thumbnail_url": asset.thumbnail_url,
                    "published_at": asset.published_at.isoformat() if asset.published_at else None,
                },
            )

            await orchestrator.process_video(source)
            return True

        except Exception as exc:
            logger.error(
                "[DiscoveryService] Submission failed for %s: %s", asset.dedup_key, exc
            )
            return False


_singleton: FootageDiscoveryService | None = None


def get_footage_discovery_service() -> FootageDiscoveryService:
    global _singleton
    if _singleton is None:
        _singleton = FootageDiscoveryService()
    return _singleton
