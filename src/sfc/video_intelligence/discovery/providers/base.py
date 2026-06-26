"""Abstract base class for footage discovery providers."""

from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sfc.video_intelligence.discovery.models import DiscoveredAsset, DiscoverySourceType

logger = logging.getLogger("sfc.video_intelligence.discovery")


class FootageProvider(abc.ABC):
    """Abstract footage discovery provider.

    Each provider scans one type of source (YouTube channel, RSS media feed,
    local folder, or direct URL list) and returns a list of DiscoveredAsset
    objects that the discovery service can deduplicate, download, and submit.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique provider name (used in logs and dedup keys)."""
        ...

    @property
    @abc.abstractmethod
    def source_type(self) -> "DiscoverySourceType":
        """DiscoverySourceType for assets produced by this provider."""
        ...

    @property
    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Return True only if the required env vars are present and the
        provider-specific enable flag is set."""
        ...

    @abc.abstractmethod
    async def discover(self) -> "list[DiscoveredAsset]":
        """Scan the source and return newly-found assets.

        Implementations must:
        - Never raise — catch all exceptions internally and return an empty list
        - Set asset.provider_name = self.name
        - Set asset.source_type = self.source_type.value
        - Leave asset.local_path empty (downloader fills it in)
        - Leave asset.status = DiscoveryStatus.PENDING
        """
        ...
