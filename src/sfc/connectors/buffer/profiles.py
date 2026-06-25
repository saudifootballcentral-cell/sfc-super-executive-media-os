"""Buffer profile discovery — maps platform accounts to Buffer profile IDs.

Discovery order:
  1. Environment variable overrides (BUFFER_X_PROFILE_ID etc.) — fastest
  2. GraphQL channels query (for API Key tokens)
  3. REST profiles.json (for OAuth tokens) — legacy fallback
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from sfc.connectors.buffer.api_client import BufferAPIClient, get_buffer_api_client
from sfc.connectors.buffer.graphql_client import (
    BufferGraphQLChannel,
    BufferGraphQLClient,
    get_buffer_graphql_client,
)

logger = logging.getLogger("sfc.connectors.buffer.profiles")

_SUPPORTED_SERVICES = {"x", "twitter", "youtube", "instagram", "facebook", "tiktok", "linkedin", "threads"}

# GraphQL service names sometimes differ from REST — normalise here
_GQL_SERVICE_MAP = {
    "twitter": "x",
    "instagramBusiness": "instagram",
    "instagramPersonal": "instagram",
    "facebookPage": "facebook",
    "facebookGroup": "facebook",
    "linkedIn": "linkedin",
    "tikTok": "tiktok",
}


@dataclass
class BufferProfile:
    profile_id: str
    service: str
    formatted_service: str
    service_username: str
    formatted_username: str
    avatar: str
    timezone: str
    utc_offset: int
    raw: dict[str, Any] = field(default_factory=dict)
    source: str = "rest"  # "graphql" | "rest" | "env"

    @property
    def platform_key(self) -> str:
        """Normalised key: 'twitter' → 'x', else service name."""
        if self.service in ("twitter", "x"):
            return "x"
        return self.service


class BufferProfileManager:
    """Discovers and caches Buffer profile IDs for connected social accounts."""

    def __init__(
        self,
        client: BufferAPIClient | None = None,
        graphql_client: BufferGraphQLClient | None = None,
    ) -> None:
        self._client = client or get_buffer_api_client()
        self._gql = graphql_client or get_buffer_graphql_client()
        self._profiles: list[BufferProfile] = []
        self._loaded = False
        self._env_ids: dict[str, str] = {
            "x": os.environ.get("BUFFER_X_PROFILE_ID", ""),
            "youtube": os.environ.get("BUFFER_YOUTUBE_PROFILE_ID", ""),
            "instagram": os.environ.get("BUFFER_INSTAGRAM_PROFILE_ID", "buf_ig_mock"),
            "threads": os.environ.get("BUFFER_THREADS_PROFILE_ID", "buf_th_mock"),
            "facebook": os.environ.get("BUFFER_FACEBOOK_PROFILE_ID", "buf_fb_mock"),
            "tiktok": os.environ.get("BUFFER_TIKTOK_PROFILE_ID", "buf_tt_mock"),
            "linkedin": os.environ.get("BUFFER_LINKEDIN_PROFILE_ID", ""),
        }

    async def get_profiles(self, force_refresh: bool = False) -> list[BufferProfile]:
        """Return all connected Buffer profiles.

        Discovery order: GraphQL channels → REST profiles.json → dry-run stubs.
        """
        if self._loaded and not force_refresh:
            return self._profiles

        token = os.environ.get("BUFFER_ACCESS_TOKEN", "")

        # Try GraphQL first for API Key tokens
        if BufferGraphQLClient.is_api_key(token):
            profiles = await self._fetch_via_graphql()
            if profiles is not None:
                self._profiles = profiles
                self._loaded = True
                return self._profiles

        # REST fallback
        profiles = await self._fetch_via_rest()
        if profiles is not None:
            self._profiles = profiles
            self._loaded = True
            return self._profiles

        # Dry-run stubs as last resort
        self._profiles = self._dry_run_profiles()
        self._loaded = True
        return self._profiles

    async def get_profile_id(self, platform: str) -> str | None:
        """Return the Buffer profile_id for the given platform key, or None."""
        key = "x" if platform in ("twitter", "x") else platform
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
    # Internal — GraphQL path
    # ------------------------------------------------------------------

    async def _fetch_via_graphql(self) -> list[BufferProfile] | None:
        try:
            channels = await self._gql.get_channels()
            if not channels and self._gql.is_live:
                # Live mode returned empty — not a dry-run, just no channels
                logger.info("[BufferProfiles] GraphQL returned 0 channels")
                return []
            if not channels:
                # Dry-run or no token
                return None
            profiles = [self._gql_channel_to_profile(c) for c in channels]
            logger.info("[BufferProfiles] Loaded %d profiles via GraphQL", len(profiles))
            return profiles
        except Exception as exc:
            logger.warning("[BufferProfiles] GraphQL channel fetch failed: %s", exc)
            return None

    def _gql_channel_to_profile(self, ch: BufferGraphQLChannel) -> BufferProfile:
        service = _GQL_SERVICE_MAP.get(ch.service, ch.service).lower()
        username = ch.handle or ch.name
        return BufferProfile(
            profile_id=ch.channel_id,
            service=service,
            formatted_service=service.title(),
            service_username=username,
            formatted_username=f"@{username}" if username and not username.startswith("@") else username,
            avatar=ch.avatar,
            timezone="UTC",
            utc_offset=0,
            raw=ch.raw,
            source="graphql",
        )

    # ------------------------------------------------------------------
    # Internal — REST path
    # ------------------------------------------------------------------

    async def _fetch_via_rest(self) -> list[BufferProfile] | None:
        try:
            data = await self._client.get("profiles.json")
            # profiles.json returns a list; other responses (dry_run, errors) return a dict
            if isinstance(data, dict) and data.get("dry_run"):
                logger.info("[BufferProfiles][DRY-RUN] Profile discovery skipped")
                return None
            raw_list = data if isinstance(data, list) else data.get("profiles", [])
            profiles = self._parse_rest_profiles(raw_list)
            logger.info("[BufferProfiles] Loaded %d profiles via REST", len(profiles))
            return profiles
        except Exception as exc:
            logger.error("[BufferProfiles] REST profile fetch failed: %s", exc)
            return None

    def _parse_rest_profiles(self, raw: list[dict[str, Any]]) -> list[BufferProfile]:
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
                source="rest",
            ))
        return profiles

    def _dry_run_profiles(self) -> list[BufferProfile]:
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
                    source="env",
                ))
        return profiles


_singleton: BufferProfileManager | None = None


def get_buffer_profile_manager() -> BufferProfileManager:
    global _singleton
    if _singleton is None:
        _singleton = BufferProfileManager()
    return _singleton
