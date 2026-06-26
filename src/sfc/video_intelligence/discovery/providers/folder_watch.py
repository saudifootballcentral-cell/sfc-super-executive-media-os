"""Local folder-watch footage discovery provider.

Scans a directory for video files that have not been seen before.

Enable:  FOLDER_WATCH_DISCOVERY_ENABLED=true
Config:  FOOTAGE_WATCH_DIR=/path/to/footage   (required)
         FOLDER_WATCH_RIGHTS_STATUS=owned      (default: owned — it's your footage)
         FOLDER_WATCH_RECURSIVE=true           (scan sub-directories; default false)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sfc.video_intelligence.discovery.models import (
    DiscoveredAsset,
    DiscoverySourceType,
    DiscoveryStatus,
)
from sfc.video_intelligence.discovery.providers.base import FootageProvider

logger = logging.getLogger("sfc.video_intelligence.discovery.folder_watch")

_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mts", ".m2ts"}


class FolderWatchProvider(FootageProvider):

    @property
    def name(self) -> str:
        return "folder_watch"

    @property
    def source_type(self) -> DiscoverySourceType:
        return DiscoverySourceType.FOLDER_WATCH

    @property
    def is_enabled(self) -> bool:
        return (
            os.environ.get("FOLDER_WATCH_DISCOVERY_ENABLED", "false").lower() == "true"
            and bool(os.environ.get("FOOTAGE_WATCH_DIR", "").strip())
        )

    def _watch_dir(self) -> Path:
        return Path(os.environ.get("FOOTAGE_WATCH_DIR", ""))

    def _rights_status(self) -> str:
        return os.environ.get("FOLDER_WATCH_RIGHTS_STATUS", "owned")

    def _recursive(self) -> bool:
        return os.environ.get("FOLDER_WATCH_RECURSIVE", "false").lower() == "true"

    async def discover(self) -> list[DiscoveredAsset]:
        if not self.is_enabled:
            return []

        watch_dir = self._watch_dir()
        if not watch_dir.is_dir():
            logger.warning("[FolderWatchProvider] FOOTAGE_WATCH_DIR does not exist: %s", watch_dir)
            return []

        assets: list[DiscoveredAsset] = []
        try:
            glob_pattern = "**/*" if self._recursive() else "*"
            for path in watch_dir.glob(glob_pattern):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in _VIDEO_EXTENSIONS:
                    continue
                asset = self._make_asset(path)
                assets.append(asset)
            logger.info("[FolderWatchProvider] dir=%s found=%d", watch_dir, len(assets))
        except Exception as exc:
            logger.warning("[FolderWatchProvider] scan error: %s", exc)

        return assets

    def _make_asset(self, path: Path) -> DiscoveredAsset:
        stat = path.stat()
        return DiscoveredAsset(
            title=path.stem,
            local_path=str(path.resolve()),
            source_type=self.source_type.value,
            rights_status=self._rights_status(),
            provider_name=self.name,
            status=DiscoveryStatus.PENDING,
            metadata={
                "file_size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "extension": path.suffix.lower(),
            },
        )
