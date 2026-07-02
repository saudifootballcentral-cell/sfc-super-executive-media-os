"""Script Generation Service — uses Claude to write video scripts from a topic.

Uses claude-opus-4-8 with adaptive thinking and streaming for long output.
Returns a structured VideoScript with per-scene narration in Arabic.
"""

from __future__ import annotations

import json
import logging
import os
from uuid import uuid4

from sfc.video_intelligence.script.models import ScriptScene, VideoScript

logger = logging.getLogger("sfc.video_intelligence.script")

_SYSTEM_PROMPT = """أنت منتج محتوى رياضي محترف لقناة سعودي فوتبول سنترال (SFC).
مهمتك: كتابة سكريبت فيديو رياضي قصير باللغة العربية مع وصف بصري بالإنجليزية.

أخرج JSON صارماً فقط بهذا الشكل:
{
  "topic": "...",
  "style": "sports_highlight",
  "scenes": [
    {
      "title": "...",
      "description": "Visual description in English for AI video generation",
      "narration": "النص العربي للتعليق الصوتي",
      "duration_seconds": 5.0,
      "visual_style": "energetic",
      "keywords": ["keyword1", "keyword2"]
    }
  ]
}

القيم المسموح بها لـ visual_style: energetic, calm, dramatic, celebratory, tense
لا تضف أي نص خارج JSON."""

_singleton: "ScriptGenerationService | None" = None


def get_script_generation_service() -> "ScriptGenerationService":
    global _singleton
    if _singleton is None:
        _singleton = ScriptGenerationService()
    return _singleton


class ScriptGenerationService:
    """Generates structured video scripts using Claude claude-opus-4-8."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(
        self,
        topic: str,
        duration_secs: float = 60.0,
        style: str = "sports_highlight",
        language: str = "ar",
        num_scenes: int | None = None,
    ) -> VideoScript:
        if num_scenes is None:
            num_scenes = max(2, int(duration_secs / 10))

        if not self.is_configured:
            logger.warning("[Script] ANTHROPIC_API_KEY not set — returning stub script")
            return self._stub_script(topic, duration_secs, num_scenes, style, language)

        try:
            return await self._generate_with_claude(
                topic, duration_secs, style, language, num_scenes
            )
        except Exception as exc:
            logger.error("[Script] Claude generation failed: %s — falling back to stub", exc)
            return self._stub_script(topic, duration_secs, num_scenes, style, language)

    async def _generate_with_claude(
        self,
        topic: str,
        duration_secs: float,
        style: str,
        language: str,
        num_scenes: int,
    ) -> VideoScript:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        user_msg = (
            f"اكتب سكريبت فيديو رياضي عن: {topic}\n"
            f"المدة الإجمالية: {duration_secs} ثانية\n"
            f"عدد المشاهد: {num_scenes}\n"
            f"الأسلوب: {style}\n"
            f"اللغة: {language}"
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

        return self._parse_script(raw_text, topic, duration_secs, style, language)

    def _parse_script(
        self,
        raw: str,
        topic: str,
        duration_secs: float,
        style: str,
        language: str,
    ) -> VideoScript:
        raw = raw.strip()
        # Extract JSON if wrapped in markdown code fences
        if "```" in raw:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            raw = raw[start:end] if start >= 0 and end > 0 else raw

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[Script] JSON parse failed — returning stub")
            return self._stub_script(topic, duration_secs, 3, style, language)

        raw_scenes = data.get("scenes", [])
        if not raw_scenes:
            logger.warning("[Script] Claude returned no scenes — returning stub")
            return self._stub_script(topic, duration_secs, 3, style, language)

        default_scene_dur = duration_secs / len(raw_scenes)
        scenes: list[ScriptScene] = []
        for i, s in enumerate(raw_scenes):
            scenes.append(ScriptScene(
                scene_id=str(uuid4()),
                title=s.get("title", f"Scene {i + 1}"),
                description=s.get("description", ""),
                narration=s.get("narration", ""),
                duration_seconds=float(s.get("duration_seconds", default_scene_dur)),
                visual_style=s.get("visual_style", "energetic"),
                keywords=s.get("keywords", []),
            ))

        total = sum(s.duration_seconds for s in scenes) or duration_secs

        script = VideoScript(
            topic=data.get("topic", topic),
            total_duration_seconds=total,
            scenes=scenes,
            language=language,
            style=data.get("style", style),
        )
        logger.info(
            "[Script] Generated script topic=%s scenes=%d total_secs=%.1f",
            topic, len(scenes), total,
        )
        return script

    def _stub_script(
        self,
        topic: str,
        duration_secs: float,
        num_scenes: int,
        style: str,
        language: str,
    ) -> VideoScript:
        scene_dur = duration_secs / max(1, num_scenes)
        scenes = [
            ScriptScene(
                scene_id=str(uuid4()),
                title=f"مشهد {i + 1}",
                description=f"Dynamic sports footage showing {topic} — scene {i + 1}",
                narration=f"هذا المشهد {i + 1} من فيديو {topic}",
                duration_seconds=scene_dur,
                visual_style="energetic" if i % 2 == 0 else "dramatic",
                keywords=["football", "Saudi", "SPL"],
            )
            for i in range(num_scenes)
        ]
        return VideoScript(
            topic=topic,
            total_duration_seconds=duration_secs,
            scenes=scenes,
            language=language,
            style=style,
            generated_by="stub",
        )

    def reset_for_test(self) -> None:
        pass
