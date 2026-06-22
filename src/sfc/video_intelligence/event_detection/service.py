"""Sports Event Detection Service — keyword and AI-assisted event recognition."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.video_intelligence.event_detection.models import (
    EventDetectionResult,
    SportEvent,
    SportEventType,
)
from sfc.video_intelligence.shared.constants import (
    EVENT_HIGHLIGHT_WEIGHTS,
    is_video_processing_enabled,
)
from sfc.video_intelligence.understanding.models import VideoUnderstandingResult

logger = logging.getLogger("sfc.video_intelligence.event_detection")

_singleton: "SportEventDetectionService | None" = None

# Arabic/English keyword → event type mapping
_KEYWORD_MAP: dict[str, SportEventType] = {
    # Goals
    "هدف": SportEventType.GOAL,
    "goal": SportEventType.GOAL,
    "score": SportEventType.GOAL,
    "scored": SportEventType.GOAL,
    # Saves
    "تصدى": SportEventType.SAVE,
    "إنقاذ": SportEventType.SAVE,
    "save": SportEventType.SAVE,
    "saved": SportEventType.SAVE,
    "goalkeeper": SportEventType.SAVE,
    # Cards
    "بطاقة حمراء": SportEventType.RED_CARD,
    "red card": SportEventType.RED_CARD,
    "طرد": SportEventType.RED_CARD,
    "بطاقة صفراء": SportEventType.YELLOW_CARD,
    "yellow card": SportEventType.YELLOW_CARD,
    # Penalty
    "ركلة جزاء": SportEventType.PENALTY,
    "penalty": SportEventType.PENALTY,
    # VAR
    "var": SportEventType.VAR_REVIEW,
    "مراجعة": SportEventType.VAR_REVIEW,
    # Celebration
    "احتفال": SportEventType.CELEBRATION,
    "celebration": SportEventType.CELEBRATION,
    # Injury
    "إصابة": SportEventType.INJURY,
    "injury": SportEventType.INJURY,
    "injured": SportEventType.INJURY,
    # Substitution
    "تبديل": SportEventType.SUBSTITUTION,
    "substitution": SportEventType.SUBSTITUTION,
    "substituted": SportEventType.SUBSTITUTION,
    # Controversial
    "جدل": SportEventType.CONTROVERSIAL,
    "controversial": SportEventType.CONTROVERSIAL,
    "debate": SportEventType.CONTROVERSIAL,
    # Free kick
    "ركلة حرة": SportEventType.FREE_KICK,
    "free kick": SportEventType.FREE_KICK,
    # Corner
    "ركنية": SportEventType.CORNER,
    "corner": SportEventType.CORNER,
    # Skills
    "مهارة": SportEventType.SKILL,
    "skill": SportEventType.SKILL,
    "dribble": SportEventType.SKILL,
    # Near miss
    "كاد": SportEventType.NEAR_MISS,
    "near miss": SportEventType.NEAR_MISS,
    "close": SportEventType.NEAR_MISS,
}


def get_sport_event_detection_service() -> "SportEventDetectionService":
    global _singleton
    if _singleton is None:
        _singleton = SportEventDetectionService()
    return _singleton


class SportEventDetectionService:
    """Detects sports events from video understanding results."""

    def __init__(self) -> None:
        self._gateway = None

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def detect(
        self,
        understanding: VideoUnderstandingResult,
    ) -> EventDetectionResult:
        result = EventDetectionResult(video_id=understanding.video_id)

        if not is_video_processing_enabled():
            result.dry_run = True
            result.events = self._dry_run_events(understanding.video_id)
            result.total_events = len(result.events)
            result.high_value_events = sum(
                1 for e in result.events if e.highlight_score >= 80
            )
            return result

        events: list[SportEvent] = []

        # Keyword detection from transcript
        if understanding.has_transcript and understanding.transcript:
            events.extend(
                self._detect_from_transcript(
                    understanding.video_id, understanding.transcript
                )
            )

        # AI-assisted detection
        if self.gateway and understanding.has_transcript:
            ai_events = await self._detect_with_ai(
                understanding.video_id, understanding
            )
            events.extend(ai_events)

        # Deduplicate overlapping events (within 3 seconds)
        events = self._deduplicate(events)

        # Score all events
        for event in events:
            event.highlight_score = self._compute_highlight_score(event)

        result.events = events
        result.total_events = len(events)
        result.high_value_events = sum(
            1 for e in events if e.highlight_score >= 80
        )
        logger.info(
            "[EventDetection] video_id=%s total=%d high_value=%d",
            understanding.video_id,
            result.total_events,
            result.high_value_events,
        )
        return result

    def _detect_from_transcript(
        self, video_id: str, transcript: Any
    ) -> list[SportEvent]:
        events: list[SportEvent] = []
        # Sort longer keywords first so "goalkeeper" is checked before "goal"
        sorted_keywords = sorted(_KEYWORD_MAP.items(), key=lambda kv: len(kv[0]), reverse=True)
        for segment in transcript.segments:
            text_lower = segment.text.lower()
            for keyword, event_type in sorted_keywords:
                if keyword in text_lower:
                    event = SportEvent(
                        video_id=video_id,
                        event_type=event_type,
                        start_seconds=max(0.0, segment.start_seconds - 3.0),
                        end_seconds=segment.end_seconds + 8.0,
                        confidence=0.75,
                        description=f"Detected '{keyword}' in transcript",
                        metadata={"source": "keyword", "keyword": keyword},
                    )
                    events.append(event)
                    break  # one event per segment
        return events

    async def _detect_with_ai(
        self, video_id: str, understanding: VideoUnderstandingResult
    ) -> list[SportEvent]:
        if not understanding.transcript:
            return []
        try:
            from sfc.ai.model_gateway import ModelRequest
            excerpt = understanding.transcript.full_text[:1000]
            response = await self.gateway.complete(
                ModelRequest(
                    prompt=(
                        "Identify sports events in this transcript. "
                        "For each event return: type, start_seconds, end_seconds. "
                        "Event types: goal, save, penalty, red_card, yellow_card, "
                        "celebration, controversy, skill, near_miss. "
                        f"Transcript: {excerpt}"
                        "\nRespond as comma-separated lines: type,start,end"
                    ),
                    max_tokens=200,
                )
            )
            return self._parse_ai_events(video_id, response.content)
        except Exception:
            return []

    def _parse_ai_events(
        self, video_id: str, raw: str
    ) -> list[SportEvent]:
        events = []
        for line in raw.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                try:
                    etype_str = parts[0].lower().replace(" ", "_")
                    etype = SportEventType(etype_str)
                    start = float(parts[1])
                    end = float(parts[2])
                    events.append(
                        SportEvent(
                            video_id=video_id,
                            event_type=etype,
                            start_seconds=start,
                            end_seconds=end,
                            confidence=0.85,
                            description="AI-detected event",
                            metadata={"source": "ai"},
                        )
                    )
                except (ValueError, KeyError):
                    continue
        return events

    def _deduplicate(self, events: list[SportEvent]) -> list[SportEvent]:
        if not events:
            return events
        events = sorted(events, key=lambda e: e.start_seconds)
        deduped = [events[0]]
        for ev in events[1:]:
            last = deduped[-1]
            if (
                ev.event_type == last.event_type
                and abs(ev.start_seconds - last.start_seconds) < 3.0
            ):
                continue
            deduped.append(ev)
        return deduped

    def _compute_highlight_score(self, event: SportEvent) -> float:
        weight = EVENT_HIGHLIGHT_WEIGHTS.get(event.event_type.value, 0.5)
        confidence_bonus = event.confidence * 10
        base = weight * 85
        return min(100.0, round(base + confidence_bonus, 1))

    def _dry_run_events(self, video_id: str) -> list[SportEvent]:
        templates = [
            (SportEventType.GOAL, 45.0, 62.0, "Goal scored"),
            (SportEventType.SAVE, 78.0, 88.0, "Goalkeeper save"),
            (SportEventType.CELEBRATION, 62.0, 72.0, "Goal celebration"),
        ]
        events = []
        for etype, start, end, desc in templates:
            e = SportEvent(
                video_id=video_id,
                event_type=etype,
                start_seconds=start,
                end_seconds=end,
                confidence=0.90,
                description=f"[DRY RUN] {desc}",
                highlight_score=self._compute_highlight_score(
                    SportEvent(
                        video_id=video_id,
                        event_type=etype,
                        start_seconds=start,
                        end_seconds=end,
                        confidence=0.90,
                    )
                ),
                metadata={"dry_run": True},
            )
            events.append(e)
        return events
