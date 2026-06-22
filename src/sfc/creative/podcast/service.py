"""AI Podcast Factory Service — generates full podcast episodes for SFC."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.creative.podcast.models import (
    PodcastEpisode,
    PodcastSegment,
    PodcastSegmentType,
    PodcastType,
)

logger = logging.getLogger("sfc.creative.podcast")

_singleton: "PodcastFactoryService | None" = None


def get_podcast_factory_service() -> "PodcastFactoryService":
    global _singleton
    if _singleton is None:
        _singleton = PodcastFactoryService()
    return _singleton


class PodcastFactoryService:
    """Generates full AI podcast episodes for SFC media."""

    _EPISODE_COUNTER: dict[str, int] = {}

    def __init__(self) -> None:
        self._gateway = None
        self._episodes: list[PodcastEpisode] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def generate_episode(
        self,
        episode_title: str,
        podcast_type: PodcastType = PodcastType.DAILY_SHOW,
        narratives: list[str] | None = None,
        context: dict[str, Any] | None = None,
        season: int = 1,
    ) -> PodcastEpisode:
        """Generate a complete podcast episode with all segments."""
        context = context or {}
        narratives = narratives or []
        ep_num = self._next_episode_number(podcast_type)
        segments = await self._generate_segments(episode_title, podcast_type, narratives, context)
        full_script = self._assemble_script(segments)
        total_duration = sum(s.duration_minutes for s in segments)
        description = await self._generate_description(episode_title, podcast_type, segments)
        show_notes = self._generate_show_notes(segments, narratives)
        chapters = self._build_chapters(segments)
        tags = self._build_tags(podcast_type, narratives)

        episode = PodcastEpisode(
            podcast_type=podcast_type,
            episode_title=episode_title,
            episode_number=ep_num,
            season=season,
            segments=segments,
            full_script=full_script,
            total_duration_minutes=round(total_duration, 1),
            description=description,
            show_notes=show_notes,
            chapters=chapters,
            tags=tags,
            publishing_metadata={
                "platform": "spotify",
                "requires_approval": True,
                "language": "arabic",
                "category": "sports",
            },
        )
        self._episodes.append(episode)
        logger.info(
            "[PodcastFactory] Episode generated | type=%s ep=%d duration=%.0fmin segments=%d",
            podcast_type.value,
            ep_num,
            total_duration,
            len(segments),
        )
        return episode

    def _next_episode_number(self, podcast_type: PodcastType) -> int:
        key = podcast_type.value
        self._EPISODE_COUNTER[key] = self._EPISODE_COUNTER.get(key, 0) + 1
        return self._EPISODE_COUNTER[key]

    async def _generate_segments(
        self,
        title: str,
        podcast_type: PodcastType,
        narratives: list[str],
        context: dict[str, Any],
    ) -> list[PodcastSegment]:
        structure = self._episode_structure(podcast_type)
        segments: list[PodcastSegment] = []
        for i, (seg_type, duration) in enumerate(structure):
            talking_points = self._talking_points_for(seg_type, title, narratives, i)
            script = await self._generate_segment_script(
                title, seg_type, talking_points, podcast_type
            )
            segments.append(
                PodcastSegment(
                    segment_number=i + 1,
                    segment_type=seg_type,
                    title=f"{seg_type.value.replace('_', ' ').title()} — {title[:30]}",
                    script=script,
                    duration_minutes=duration,
                    speaker="host" if seg_type != PodcastSegmentType.INTERVIEW else "guest",
                    talking_points=talking_points,
                )
            )
        return segments

    def _episode_structure(
        self, podcast_type: PodcastType
    ) -> list[tuple[PodcastSegmentType, float]]:
        structures = {
            PodcastType.DAILY_SHOW: [
                (PodcastSegmentType.INTRO, 1.5),
                (PodcastSegmentType.CONTENT, 8.0),
                (PodcastSegmentType.ANALYSIS, 6.0),
                (PodcastSegmentType.SPONSOR, 1.0),
                (PodcastSegmentType.OUTRO, 1.5),
            ],
            PodcastType.MATCH_RECAP: [
                (PodcastSegmentType.INTRO, 1.0),
                (PodcastSegmentType.CONTENT, 10.0),
                (PodcastSegmentType.ANALYSIS, 8.0),
                (PodcastSegmentType.OUTRO, 1.0),
            ],
            PodcastType.TRANSFER_SHOW: [
                (PodcastSegmentType.INTRO, 1.5),
                (PodcastSegmentType.CONTENT, 12.0),
                (PodcastSegmentType.INTERVIEW, 8.0),
                (PodcastSegmentType.ANALYSIS, 5.0),
                (PodcastSegmentType.OUTRO, 1.5),
            ],
            PodcastType.WORLD_CUP_SHOW: [
                (PodcastSegmentType.INTRO, 2.0),
                (PodcastSegmentType.CONTENT, 15.0),
                (PodcastSegmentType.ANALYSIS, 10.0),
                (PodcastSegmentType.INTERVIEW, 10.0),
                (PodcastSegmentType.OUTRO, 3.0),
            ],
            PodcastType.TACTICAL_SHOW: [
                (PodcastSegmentType.INTRO, 1.5),
                (PodcastSegmentType.CONTENT, 10.0),
                (PodcastSegmentType.ANALYSIS, 12.0),
                (PodcastSegmentType.OUTRO, 1.5),
            ],
        }
        return structures.get(
            podcast_type,
            [
                (PodcastSegmentType.INTRO, 1.5),
                (PodcastSegmentType.CONTENT, 8.0),
                (PodcastSegmentType.OUTRO, 1.5),
            ],
        )

    def _talking_points_for(
        self,
        seg_type: PodcastSegmentType,
        title: str,
        narratives: list[str],
        index: int,
    ) -> list[str]:
        if seg_type == PodcastSegmentType.INTRO:
            return [f"Welcome to SFC — {title}", "Today's top stories", "What to expect"]
        if seg_type == PodcastSegmentType.OUTRO:
            return ["Summary of key points", "Subscribe to SFC podcast", "Next episode preview"]
        if seg_type == PodcastSegmentType.SPONSOR:
            return ["Sponsor acknowledgement", "SFC partners"]
        points = [narratives[i] for i in range(min(3, len(narratives)))]
        if not points:
            points = [f"Key point {j+1} for {title}" for j in range(3)]
        return points

    async def _generate_segment_script(
        self,
        episode_title: str,
        seg_type: PodcastSegmentType,
        talking_points: list[str],
        podcast_type: PodcastType,
    ) -> str:
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                points_str = "; ".join(talking_points[:3])
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Write a {seg_type.value} podcast script segment for SFC sports podcast. "
                            f"Episode: '{episode_title}'. Type: {podcast_type.value}. "
                            f"Talking points: {points_str}. "
                            "Arabic sports broadcast style. 2-4 sentences."
                        ),
                        max_tokens=200,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        points_str = " | ".join(talking_points[:2])
        return (
            f"[{seg_type.value.upper()}] {episode_title}: {points_str}. "
            "SFC — كرة القدم السعودية."
        )

    def _assemble_script(self, segments: list[PodcastSegment]) -> str:
        return "\n\n".join(
            f"=== {s.segment_type.value.upper()} ===\n{s.script}" for s in segments
        )

    async def _generate_description(
        self, title: str, podcast_type: PodcastType, segments: list[PodcastSegment]
    ) -> str:
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Write a podcast episode description (2-3 sentences) for: '{title}'. "
                            f"Type: {podcast_type.value}. SFC Saudi football. Arabic-first."
                        ),
                        max_tokens=120,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return (
            f"In this {podcast_type.value.replace('_', ' ')} episode, SFC covers: {title}. "
            "All the latest from Saudi football brought to you by SFC Media."
        )

    def _generate_show_notes(
        self, segments: list[PodcastSegment], narratives: list[str]
    ) -> str:
        notes = ["## Show Notes", ""]
        for i, seg in enumerate(segments):
            notes.append(f"**{i+1}. {seg.title}** ({seg.duration_minutes:.0f} min)")
            for pt in seg.talking_points[:2]:
                notes.append(f"  - {pt}")
        if narratives:
            notes.extend(["", "## Topics Covered", *[f"- {n}" for n in narratives[:5]]])
        return "\n".join(notes)

    def _build_chapters(self, segments: list[PodcastSegment]) -> list[dict]:
        chapters = []
        current_time = 0.0
        for seg in segments:
            chapters.append({
                "title": seg.title,
                "start_time_seconds": int(current_time * 60),
                "duration_minutes": seg.duration_minutes,
            })
            current_time += seg.duration_minutes
        return chapters

    def _build_tags(self, podcast_type: PodcastType, narratives: list[str]) -> list[str]:
        base_tags = ["SFC", "Saudi Football", "كرة القدم السعودية", podcast_type.value]
        narrative_tags = [n[:20] for n in narratives[:3]]
        return base_tags + narrative_tags

    def get_recent_episodes(self, limit: int = 10) -> list[PodcastEpisode]:
        return self._episodes[-limit:]
