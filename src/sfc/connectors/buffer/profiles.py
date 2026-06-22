"""Buffer profile discovery — maps platform accounts to Buffer profile IDs."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from sfc.connectors.buffer.api_client import BufferAPIClient, get_buffer_api_client

logger = logging.getLogger("sfc.connectors.buffer.profiles")

# Platforms supported for publishing via Buffer in Package 9B
_SUPPORTED_SERVICES = {"x", "twitter", "youtube", "instagram", "facebook", "tiktok", "linkedin", "threads"}


@dataclass
class BufferProfile:
    profile_id: str
    service: str          # "twitter", "youtube", "instagram", etc.
    formatted_service: str
    service_username: str
    formatted_username: str
    avatar: str
    timezone: str
    utc_offset: int
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def platform_key(self) -> str:
        """Normalised key: 'twitter' → 'x', else service name."""
        if self.service in ("twitter", "x"):
            return "x"
        return self.service


class BufferProfileManager:
    """Discovers and caches Buffer profile IDs for connected social accounts."""

    def __init__(self, client: BufferAPIClient | None = None) -> None:
        self._client = client or get_buffer_api_client()
        self._profiles: list[BufferProfile] = []
        self._loaded = False
        # Env-var overrides for specific platforms (avoids extra API call in tests)
        self._env_ids: dict[str, str] = {
            "x": os.environ.get("BUFFER_X_PROFILE_ID", ""),
            "youtube": os.environ.get("BUFFER_YOUTUBE_PROFILE_ID", ""),
            "instagram": os.environ.get("BUFFER_INSTAGRAM_PROFILE_ID", os.environ.get("BUFFER_INSTAGRAM_PROFILE_ID", "buf_ig_mock")),
            "threads": os.environ.get("BUFFER_THREADS_PROFILE_ID", "buf_th_mock"),
            "facebook": os.environ.get("BUFFER_FACEBOOK_PROFILE_ID", "buf_fb_mock"),
            "tiktok": os.environ.get("BUFFER_TIKTOK_PROFILE_ID", "buf_tt_mock"),
            "linkedin": os.environ.get("BUFFER_LINKEDIN_PROFILE_ID", ""),
        }

    async def get_profiles(self, force_refresh: bool = False) -> list[BufferProfile]:
        """Return all connected Buffer profiles, fetching from API if needed."""
        if self._loaded and not force_refresh:
            return self._profiles
        try:
            data = await self._client.get("profiles.json")
            if data.get("dry_run"):
                logger.info("[BufferProfiles][DRY-RUN] Profile discovery skipped")
                self._profiles = self._dry_run_profiles()
                self._loaded = True
                return self._profiles
            profiles = self._parse_profiles(data if isinstance(data, list) else data.get("profiles", []))
            self._profiles = profiles
            self._loaded = True
            logger.info("[BufferProfiles] Loaded %d profiles", len(profiles))
            return profiles
        except Exception as exc:
            logger.error("[BufferProfiles] Failed to fetch profiles: %s", exc)
            self._profiles = self._dry_run_profiles()
            self._loaded = True
            return self._profiles

    async def get_profile_id(self, platform: str) -> str | None:
        """Return the Buffer profile_id for the given platform key, or None."""
        key = "x" if platform in ("twitter", "x") else platform
        # Check env overrides first
        env_id = self._env_ids.get(key, "")
        if env_id:
            return env_id
        profiles = await self.get_profiles()
        for p in profiles:
            if p.platform_key == key:
                return p.profile_id
        return None

    async def get_profiles_for_platforms(self, platforms: list[str]) -> dict[str, str]:
        """Return {platform: profile_id} for the given list of platforms."""
        result: dict[str, str] = {}
        for plat in platforms:
            pid = await self.get_profile_id(plat)
            if pid:
                result[plat] = pid
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _parse_profiles(self, raw: list[dict[str, Any]]) -> list[BufferProfile]:
        profiles: list[BufferProfile] = []
        for item in raw:
            service = item.get("service", "")
            if service not in _SUPPORTED_SERVICES:
                continue
            profiles.append(BufferProfile(
                profile_id=str(item.get("_id", item.get("id", ""))),
                service=service,
                formatted_service=item.get("formatted_service", service),
                service_username=item.get("service_username", ""),
                formatted_username=item.get("formatted_username", ""),
                avatar=item.get("avatar", ""),
                timezone=item.get("timezone", "UTC"),
                utc_offset=int(item.get("utc_offset", 0)),
                raw=item,
            ))
        return profiles

    def _dry_run_profiles(self) -> list[BufferProfile]:
        """Return placeholder profiles matching env-var IDs."""
        profiles = []
        for key, pid in self._env_ids.items():
            if pid:
                profiles.append(BufferProfile(
                    profile_id=pid,
                    service=key,
                    formatted_service=key.title(),
                    service_username=f"sfc_{key}",
                    formatted_username=f"@sfc_{key}",
                    avatar="",
                    timezone="Asia/Riyadh",
                    utc_offset=180,
                ))
        return profiles


_singleton: BufferProfileManager | None = None


def get_buffer_profile_manager() -> BufferProfileManager:
    global _singleton
    if _singleton is None:
        _singleton = BufferProfileManager()
    return _singleton
