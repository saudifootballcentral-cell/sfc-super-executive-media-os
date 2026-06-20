"""Creative Node — multimedia asset production briefs.

Sequential — starts after editorial_node completes.
Package 2: CreativeDivision will replace the stub logic with real AI generation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.creative")

# Asset spec per format
_ASSET_SPECS: dict[str, dict[str, Any]] = {
    "tiktok_video": {"aspect_ratio": "9:16", "max_duration_s": 60, "format": "mp4", "provider": "veo"},
    "instagram_reel": {"aspect_ratio": "9:16", "max_duration_s": 90, "format": "mp4", "provider": "veo"},
    "youtube_short": {"aspect_ratio": "9:16", "max_duration_s": 60, "format": "mp4", "provider": "kling"},
    "youtube_long": {"aspect_ratio": "16:9", "format": "mp4", "provider": "runway"},
    "thumbnail": {"dimensions": "1280x720", "format": "jpg", "provider": "internal"},
    "poster": {"dimensions": "1080x1920", "format": "jpg", "provider": "internal"},
    "instagram_feed": {"dimensions": "1080x1080", "format": "jpg", "provider": "internal"},
    "voiceover": {"format": "mp3", "provider": "elevenlabs"},
    "social_graphic": {"dimensions": "1200x675", "format": "jpg", "provider": "internal"},
}

_PLATFORM_TO_ASSET: dict[str, list[str]] = {
    "tiktok": ["tiktok_video", "voiceover"],
    "instagram_reels": ["instagram_reel", "voiceover"],
    "instagram_stories": ["instagram_reel"],
    "instagram_feed": ["instagram_feed"],
    "youtube_shorts": ["youtube_short", "thumbnail"],
    "youtube": ["youtube_long", "thumbnail", "voiceover"],
    "x": ["social_graphic"],
    "telegram": ["social_graphic"],
    "website": ["thumbnail", "social_graphic"],
}


async def creative_node(state: SFCState) -> dict[str, Any]:
    """Node: creative

    Produces asset production briefs for every content draft.
    Each brief specifies: asset type, platform spec, copy, provider.

    Responsibilities:
    - Video generation briefs (Veo, Kling, Runway, Luma)
    - Thumbnail / poster briefs
    - Social graphic briefs
    - Voiceover briefs (ElevenLabs)
    - Match day graphic packages

    Package 2: CreativeDivision will call AI generation APIs directly.
    """
    content_drafts = state.get("content_drafts", [])
    plan = state.get("execution_plan", {})

    logger.info("[Creative] Generating asset briefs for %d draft(s)", len(content_drafts))

    if not content_drafts:
        logger.warning("[Creative] No content drafts to process")
        return {"creative_assets": [], "warnings": ["CREATIVE: No drafts to process"]}

    try:
        # ----------------------------------------------------------------
        # TODO Package 2: Replace with CreativeDivision implementation
        # - Real AI video generation via Veo/Kling/Runway/Luma
        # - Real thumbnail generation
        # - ElevenLabs voiceover generation
        # - Graphic design via internal brand templates
        # ----------------------------------------------------------------

        assets: list[dict[str, Any]] = []

        for draft in content_drafts:
            draft_platforms = draft.get("platforms", [])
            for platform in draft_platforms:
                asset_types = _PLATFORM_TO_ASSET.get(platform, ["social_graphic"])
                for asset_type_key in asset_types:
                    spec = _ASSET_SPECS.get(asset_type_key, {})
                    asset = {
                        "asset_id": str(uuid.uuid4()),
                        "content_id": draft.get("content_id"),
                        "asset_type": asset_type_key,
                        "platform": platform,
                        "spec": spec,
                        "provider": spec.get("provider", "internal"),
                        "copy": {
                            "title": draft.get("title", ""),
                            "body_preview": draft.get("body", "")[:150],
                            "is_rumor": draft.get("is_rumor", False),
                        },
                        "status": "briefed",
                        "briefed_at": datetime.utcnow().isoformat(),
                    }
                    assets.append(asset)

        # Unique providers being engaged
        providers = list({a["provider"] for a in assets})
        logger.info(
            "[Creative] %d asset brief(s) | providers: %s",
            len(assets),
            ", ".join(providers),
        )

        return {
            "creative_assets": assets,
            "pipeline_stage": "creative_complete",
        }

    except Exception as exc:
        logger.error("[Creative] Failed: %s", exc)
        return {
            "creative_assets": [],
            "errors": [f"CREATIVE: {exc}"],
        }
