"""Publisher Router — automatically selects Direct API or Buffer for each platform.

Strategy:
- If PLATFORM_PREFER_DIRECT=true (env var) → try Direct API first
- If direct credentials available → use Direct API
- Otherwise → use Buffer if Buffer has a profile for this platform
- If neither → log warning, skip platform
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("sfc.connectors.routing.publisher_router")

# ---------------------------------------------------------------------------
# Credential mapping: platform → (direct_env_var, buffer_env_var | None)
# ---------------------------------------------------------------------------
_PLATFORM_CREDENTIALS: dict[str, tuple[str, str | None]] = {
    "x":          ("X_API_KEY",               "BUFFER_ACCESS_TOKEN"),
    "youtube":    ("YOUTUBE_CLIENT_ID",        None),
    "instagram":  ("INSTAGRAM_ACCESS_TOKEN",   "BUFFER_INSTAGRAM_PROFILE_ID"),
    "tiktok":     ("TIKTOK_ACCESS_TOKEN",      "BUFFER_TIKTOK_PROFILE_ID"),
    "facebook":   ("FACEBOOK_ACCESS_TOKEN",    "BUFFER_FACEBOOK_PROFILE_ID"),
    "linkedin":   ("LINKEDIN_ACCESS_TOKEN",    "BUFFER_LINKEDIN_PROFILE_ID"),
    "telegram":   ("TELEGRAM_BOT_TOKEN",       None),
    "discord":    ("DISCORD_BOT_TOKEN",        None),
    "pinterest":  ("PINTEREST_ACCESS_TOKEN",   None),
    "reddit":     ("REDDIT_CLIENT_ID",         None),
    "medium":     ("MEDIUM_ACCESS_TOKEN",      None),
    "wordpress":  ("WORDPRESS_SITE_URL",       None),
    "email":      ("EMAIL_SMTP_HOST",          None),
    "threads":    (None,                        "BUFFER_THREADS_PROFILE_ID"),  # type: ignore[arg-type]
    "whatsapp":   ("WHATSAPP_ACCESS_TOKEN",    None),
}


class PublishResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    platform: str = ""
    route_used: str = ""  # "direct" | "buffer" | "skipped"
    post_id: str = ""
    url: str = ""
    success: bool = False
    error: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


_singleton: "PublisherRouter | None" = None


def get_publisher_router() -> "PublisherRouter":
    global _singleton
    if _singleton is None:
        _singleton = PublisherRouter()
    return _singleton


class PublisherRouter:
    """Routes content to the best available publishing path per platform."""

    def __init__(self) -> None:
        self._prefer_direct = os.environ.get("PLATFORM_PREFER_DIRECT", "").lower() == "true"

    # ------------------------------------------------------------------
    # Route resolution
    # ------------------------------------------------------------------

    def resolve_route(self, platform: str) -> str:
        """Return 'direct', 'buffer', or 'skipped' for this platform."""
        mapping = _PLATFORM_CREDENTIALS.get(platform.lower())
        if not mapping:
            return "skipped"

        direct_var, buffer_var = mapping
        has_direct = bool(direct_var and os.environ.get(direct_var, ""))
        has_buffer = bool(buffer_var and os.environ.get(buffer_var, ""))

        if self._prefer_direct and has_direct:
            return "direct"
        if has_direct:
            return "direct"
        if has_buffer:
            return "buffer"
        return "skipped"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(
        self,
        platform: str,
        text: str,
        media_url: str = "",
        extra: dict[str, Any] | None = None,
    ) -> PublishResult:
        """Publish content to the given platform via the best available route."""
        platform = platform.lower()
        route = self.resolve_route(platform)

        if route == "skipped":
            logger.warning(
                "[Router] No credentials for platform=%s — skipping", platform
            )
            return PublishResult(
                platform=platform,
                route_used="skipped",
                success=False,
                error=f"No credentials configured for {platform}",
            )

        if route == "direct":
            return await self._publish_direct(platform, text, media_url, extra or {})
        else:
            return await self._publish_buffer(platform, text, media_url, extra or {})

    async def _publish_direct(
        self,
        platform: str,
        text: str,
        media_url: str,
        extra: dict[str, Any],
    ) -> PublishResult:
        """Publish using the platform's direct API connector (mocked)."""
        try:
            result_data: dict[str, Any] = {}

            if platform == "x":
                from sfc.connectors.x.service import get_x_service
                svc = get_x_service()
                post = await svc.create_post(text=text[:280])
                result_data = {"post_id": post.platform_post_id, "url": post.url}

            elif platform == "youtube":
                from sfc.connectors.youtube.service import get_youtube_service
                from sfc.connectors.youtube.models import VideoUploadRequest
                svc = get_youtube_service()
                req = VideoUploadRequest(title=text[:100], file_url=media_url)
                result = await svc.upload_video(req)
                result_data = {"post_id": result.video_id, "url": result.url}

            elif platform == "instagram":
                from sfc.connectors.instagram.service import get_instagram_service
                svc = get_instagram_service()
                if media_url:
                    res = await svc.create_post(caption=text, image_url=media_url)
                else:
                    res = await svc.create_post(caption=text, image_url="")
                result_data = {
                    "post_id": res.get("platform_media_id", ""),
                    "url": res.get("permalink", ""),
                }

            elif platform == "facebook":
                from sfc.connectors.facebook.service import get_facebook_service
                svc = get_facebook_service()
                if media_url:
                    res = await svc.create_photo_post(message=text, photo_url=media_url)
                else:
                    res = await svc.create_post(message=text)
                result_data = {
                    "post_id": res.get("platform_post_id", ""),
                    "url": res.get("permalink", ""),
                }

            elif platform == "linkedin":
                from sfc.connectors.linkedin.service import get_linkedin_service
                svc = get_linkedin_service()
                if media_url:
                    res = await svc.create_media_post(text=text, media_url=media_url)
                else:
                    res = await svc.create_text_post(text=text)
                result_data = {
                    "post_id": res.get("post_urn", ""),
                    "url": res.get("url", ""),
                }

            elif platform == "telegram":
                from sfc.connectors.telegram.service import get_telegram_service
                svc = get_telegram_service()
                if media_url:
                    res = await svc.send_photo(text=text, photo_url=media_url)
                else:
                    res = await svc.send_message(text=text)
                result_data = {
                    "post_id": str(res.get("platform_message_id", "")),
                    "url": res.get("url", ""),
                }

            elif platform == "discord":
                from sfc.connectors.discord.service import get_discord_service
                svc = get_discord_service()
                res = await svc.send_message(content=text)
                result_data = {
                    "post_id": res.get("platform_message_id", ""),
                    "url": "",
                }

            elif platform == "tiktok":
                from sfc.connectors.tiktok.service import get_tiktok_service
                svc = get_tiktok_service()
                res = await svc.upload_video(
                    video_url=media_url,
                    title=text[:80],
                    description=text,
                    hashtags=extra.get("hashtags", []),
                )
                result_data = {
                    "post_id": res.get("platform_video_id", ""),
                    "url": res.get("share_url", ""),
                }

            elif platform == "pinterest":
                from sfc.connectors.pinterest.service import get_pinterest_service
                svc = get_pinterest_service()
                res = await svc.create_pin(
                    title=text[:100],
                    description=text,
                    image_url=media_url,
                )
                result_data = {
                    "post_id": res.get("platform_pin_id", ""),
                    "url": res.get("pin_url", ""),
                }

            elif platform == "reddit":
                from sfc.connectors.reddit.service import get_reddit_service
                svc = get_reddit_service()
                subreddit = extra.get("subreddit", "r/SaudiFootball")
                res = await svc.create_post(subreddit=subreddit, title=text[:300], text=text)
                result_data = {
                    "post_id": res.get("platform_post_id", ""),
                    "url": res.get("permalink", ""),
                }

            elif platform == "medium":
                from sfc.connectors.medium.service import get_medium_service
                svc = get_medium_service()
                res = await svc.create_post(
                    title=text[:100],
                    content_html=f"<p>{text}</p>",
                    tags=extra.get("tags", ["Saudi Football", "SPL"]),
                )
                result_data = {
                    "post_id": res.get("platform_post_id", ""),
                    "url": res.get("url", ""),
                }

            elif platform == "wordpress":
                from sfc.connectors.wordpress.service import get_wordpress_service
                svc = get_wordpress_service()
                res = await svc.create_post(
                    title=text[:200],
                    content=text,
                    excerpt=text[:280],
                    tags=extra.get("tags", []),
                )
                result_data = {
                    "post_id": str(res.get("platform_post_id", "")),
                    "url": res.get("url", ""),
                }

            elif platform == "email":
                from sfc.connectors.email.service import get_email_service
                svc = get_email_service()
                res = await svc.send_newsletter(
                    subject=text[:200],
                    html_content=f"<p>{text}</p>",
                    recipient_list=extra.get("recipients", []),
                )
                result_data = {
                    "post_id": res.get("platform_campaign_id", ""),
                    "url": "",
                }

            elif platform == "whatsapp":
                from sfc.connectors.whatsapp.service import get_whatsapp_service
                svc = get_whatsapp_service()
                to = extra.get("to", "")
                if media_url:
                    res = await svc.send_media(to=to, media_url=media_url, media_type="image", caption=text)
                else:
                    res = await svc.send_text(to=to, text=text)
                result_data = {
                    "post_id": res.get("platform_message_id", ""),
                    "url": "",
                }

            else:
                return PublishResult(
                    platform=platform,
                    route_used="direct",
                    success=False,
                    error=f"Unknown platform: {platform}",
                )

            logger.info(
                "[Router] Direct publish OK | platform=%s post_id=%s",
                platform, result_data.get("post_id", ""),
            )
            return PublishResult(
                platform=platform,
                route_used="direct",
                post_id=result_data.get("post_id", ""),
                url=result_data.get("url", ""),
                success=True,
            )

        except Exception as exc:
            logger.error("[Router] Direct publish FAILED | platform=%s error=%s", platform, exc)
            return PublishResult(
                platform=platform,
                route_used="direct",
                success=False,
                error=str(exc),
            )

    async def _publish_buffer(
        self,
        platform: str,
        text: str,
        media_url: str,
        extra: dict[str, Any],
    ) -> PublishResult:
        """Publish via Buffer multi-platform scheduler (mocked)."""
        try:
            from sfc.connectors.buffer.service import get_buffer_service
            svc = get_buffer_service()
            content_package = {
                "package_type": f"{platform}_post",
                "caption": text,
                "media_url": media_url,
                "ready_to_publish": True,
                "platforms": [platform],
                **extra,
            }
            results = await svc.publish_content_package(content_package)
            post_id = results[0].platform_post_id if results else ""
            url = results[0].post_url if results else ""
            logger.info(
                "[Router] Buffer publish OK | platform=%s post_id=%s", platform, post_id
            )
            return PublishResult(
                platform=platform,
                route_used="buffer",
                post_id=post_id,
                url=url,
                success=True,
            )
        except Exception as exc:
            logger.error("[Router] Buffer publish FAILED | platform=%s error=%s", platform, exc)
            return PublishResult(
                platform=platform,
                route_used="buffer",
                success=False,
                error=str(exc),
            )
