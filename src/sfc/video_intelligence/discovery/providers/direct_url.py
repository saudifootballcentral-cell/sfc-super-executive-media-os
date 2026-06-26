"""Direct URL footage discovery provider.

Turns an explicit list of video URLs into DiscoveredAsset objects.
Useful for one-off ingestion or curated footage URLs set via env.

Enable:  DIRECT_URL_DISCOVERY_ENABLED=true
Config:  FOOTAGE_DIRECT_URLS=https://...,https://...   (comma-separated)
         DIRECT_URL_RIGHTS_STATUS=licensed             (default: unknown)
"""

from __future__ import annotations

import logging
import os

from sfc.video_intelligence.discovery.models import (
    DiscoveredAsset,
    DiscoverySourceType,
    DiscoveryStatus,
)
from sfc.video_intelligence.discovery.providers.base import FootageProvider

logger = logging.getLogger("sfc.video_intelligence.discovery.direct_url")


class DirectUrlProvider(FootageProvider):

    @property
    def name(self) -> str:
        return "direct_url"

    @property
    def source_type(self) -> DiscoverySourceType:
        return DiscoverySourceType.DIRECT_URL

    @property
    def is_enabled(self) -> bool:
        return (
            os.environ.get("DIRECT_URL_DISCOVERY_ENABLED", "false").lower() == "true"
            and bool(os.environ.get("FOOTAGE_DIRECT_URLS", "").strip())
        )

    def _urls(self) -> list[str]:
        raw = os.environ.get("FOOTAGE_DIRECT_URLS", "")
        return [u.strip() for u in raw.split(",") if u.strip()]

    def _rights_status(self) -> str:
        return os.environ.get("DIRECT_URL_RIGHTS_STATUS", "unknown")

    async def discover(self) -> list[DiscoveredAsset]:
        if not self.is_enabled:
            return []

        assets: list[DiscoveredAsset] = []
        for url in self._urls():
            # Derive a title from the URL path segment
            title = url.rstrip("/").split("/")[-1].split("?")[0] or url
            assets.append(
                DiscoveredAsset(
                    title=title,
                    url=url,
                    source_type=self.source_type.value,
                    rights_status=self._rights_status(),
                    provider_name=self.name,
                    status=DiscoveryStatus.PENDING,
                    metadata={"raw_url": url},
                )
            )

        logger.info("[DirectUrlProvider] found=%d", len(assets))
        return assets
