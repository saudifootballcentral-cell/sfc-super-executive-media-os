"""Storyboard Generation Service — converts a VideoScript into AI video prompts.

Uses Claude claude-opus-4-8 to translate Arabic narration + visual descriptions into
optimised English prompts suitable for Kling / Runway / Luma / Pika.
"""

from __future__ import annotations

import json
import logging
import os
from uuid import uuid4

from sfc.video_intelligence.script.models import VideoScript
from sfc.video_intelligence.storyboard.models import Storyboard, StoryboardScene

logger = logging.getLogger("sfc.video_intelligence.storyboard")

_PLATFORM_ASPECT: dict[str, str] = {
    "youtube_video": "16:9",
    "youtube_short": "9:16",
    "instagram_reel": "9:16",
    "tiktok": "9:16",
    "x_video": "16:9",
}

_SYSTEM_PROMPT = """You are a professional AI video prompt engineer specializing in sports content.
Convert each script scene into an optimised prompt for AI text-to-video models (Kling, Runway, Luma).

Output strict JSON only:
{
  "scenes": [
    {
      "scene_id": "<from input>",
      "visual_prompt": "Detailed English prompt: cinematic shot of...",
      "negative_prompt": "blur, low quality, text overlays, watermark",
      "style_tags": ["cinematic", "4K", "sports"]
    }
  ]
}

Rules:
- visual_prompt must be in English, highly descriptive, 50-120 words
- Translate Arabic narration intent into visual action
- Include camera movement, lighting, mood
- negative_prompt should prevent common AI artifacts
- style_tags: 3-5 descriptive tags
- Output JSON only, no extra text."""

_singleton: "StoryboardGenerationService | None" = None


def get_storyboard_generation_service() -> "StoryboardGenerationService":
    global _singleton
    if _singleton is None:
        _singleton = StoryboardGenerationService()
    return _singleton


class StoryboardGenerationService:
    """Generates AI video prompts from a VideoScript using Claude."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def create(self, script: VideoScript, platform: str = "youtube_video") -> Storyboard:
        aspect_ratio = _PLATFORM_ASPECT.get(platform, "16:9")

        if not self.is_configured:
            logger.warning("[Storyboard] ANTHROPIC_API_KEY not set — returning stub storyboard")
            return self._stub_storyboard(script, platform, aspect_ratio)

        try:
            return await self._create_with_claude(script, platform, aspect_ratio)
        except Exception as exc:
            logger.error("[Storyboard] Claude generation failed: %s — falling back to stub", exc)
            return self._stub_storyboard(script, platform, aspect_ratio)

    async def _create_with_claude(
        self, script: VideoScript, platform: str, aspect_ratio: str
    ) -> Storyboard:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)

        scenes_input = [
            {
                "scene_id": s.scene_id,
                "title": s.title,
                "description": s.description,
                "narration_ar": s.narration,
                "visual_style": s.visual_style,
                "keywords": s.keywords,
                "duration_seconds": s.duration_seconds,
            }
            for s in script.scenes
        ]

        user_msg = (
            f"Convert these script scenes for platform={platform} "
            f"(aspect_ratio={aspect_ratio}) into AI video prompts:\n\n"
            f"{json.dumps(scenes_input, ensure_ascii=False, indent=2)}"
        )

        with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        ) as stream:
            final = stream.get_final_message()

        raw_text = ""
        for block in final.content:
            if hasattr(block, "text"):
                raw_text += block.text

        return self._parse_storyboard(raw_text, script, platform, aspect_ratio)

    def _parse_storyboard(
        self, raw: str, script: VideoScript, platform: str, aspect_ratio: str
    ) -> Storyboard:
        raw = raw.strip()
        if "```" in raw:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            raw = raw[start:end] if start >= 0 and end > 0 else raw

        # Build lookup of script scenes by scene_id
        scene_lookup = {s.scene_id: s for s in script.scenes}

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[Storyboard] JSON parse failed — returning stub")
            return self._stub_storyboard(script, platform, aspect_ratio)

        sb_scenes: list[StoryboardScene] = []
        for entry in data.get("scenes", []):
            original_id = entry.get("scene_id", "")
            original = scene_lookup.get(original_id)
            sb_scenes.append(StoryboardScene(
                scene_id=str(uuid4()),
                script_scene_id=original_id,
                visual_prompt=entry.get("visual_prompt", ""),
                negative_prompt=entry.get("negative_prompt", "blur, low quality, watermark"),
                duration_seconds=original.duration_seconds if original else 5.0,
                aspect_ratio=aspect_ratio,
                style_tags=entry.get("style_tags", []),
            ))

        total = sum(s.duration_seconds for s in sb_scenes)

        board = Storyboard(
            script_id=script.script_id,
            platform=platform,
            scenes=sb_scenes,
            total_duration_seconds=total,
        )
        logger.info(
            "[Storyboard] Created storyboard script_id=%s platform=%s scenes=%d",
            script.script_id, platform, len(sb_scenes),
        )
        return board

    def _stub_storyboard(
        self, script: VideoScript, platform: str, aspect_ratio: str
    ) -> Storyboard:
        sb_scenes = [
            StoryboardScene(
                scene_id=str(uuid4()),
                script_scene_id=s.scene_id,
                visual_prompt=(
                    f"Cinematic sports footage, {s.description}, "
                    f"dynamic camera movement, high energy, professional broadcast quality, "
                    f"Saudi football stadium, crowd cheering, vivid colors, 4K ultra HD"
                ),
                negative_prompt="blur, low quality, watermark, text overlay, cartoon, anime",
                duration_seconds=s.duration_seconds,
                aspect_ratio=aspect_ratio,
                style_tags=["cinematic", "sports", "4K", s.visual_style],
            )
            for s in script.scenes
        ]
        return Storyboard(
            script_id=script.script_id,
            platform=platform,
            scenes=sb_scenes,
            total_duration_seconds=script.total_duration_seconds,
        )

    def reset_for_test(self) -> None:
        pass
