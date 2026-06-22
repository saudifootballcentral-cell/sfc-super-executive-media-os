"""Interview & Press Conference Detection Service."""

from __future__ import annotations

import logging

from sfc.video_intelligence.ingestion.models import VideoIngestionResult, VideoSourceType
from sfc.video_intelligence.interview_detection.models import (
    InterviewDetectionResult,
    InterviewSegmentType,
    KeyQuote,
    SpeakerSegment,
)
from sfc.video_intelligence.shared.constants import is_video_processing_enabled
from sfc.video_intelligence.understanding.models import VideoUnderstandingResult

logger = logging.getLogger("sfc.video_intelligence.interview_detection")

_singleton: "InterviewDetectionService | None" = None

# Topic keywords for quote classification
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "transfer": ["transfer", "انتقال", "sign", "contract", "عقد"],
    "injury": ["injury", "إصابة", "recover", "تعافي"],
    "performance": ["performance", "أداء", "play", "match", "مباراة"],
    "tactics": ["tactics", "تكتيك", "formation", "تشكيل", "strategy"],
    "opponent": ["opponent", "منافس", "team", "فريق"],
    "ambition": ["ambition", "طموح", "goal", "هدف", "champion", "بطولة"],
}


def get_interview_detection_service() -> "InterviewDetectionService":
    global _singleton
    if _singleton is None:
        _singleton = InterviewDetectionService()
    return _singleton


class InterviewDetectionService:
    """Detects interview segments and extracts key quotes from transcripts."""

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
        ingestion: VideoIngestionResult,
    ) -> InterviewDetectionResult:
        video_id = understanding.video_id
        segment_type = self._classify_source(ingestion)
        result = InterviewDetectionResult(
            video_id=video_id,
            segment_type=segment_type,
        )

        if not is_video_processing_enabled():
            result.dry_run = True
            result.speaker_segments, result.key_quotes = self._dry_run_content(video_id)
            result.speakers_identified = 1
            result.total_duration_seconds = 120.0
            return result

        if not understanding.has_transcript or not understanding.transcript:
            result.speaker_segments = []
            result.key_quotes = []
            return result

        speaker_segs = self._extract_speaker_segments(video_id, understanding)
        quotes = await self._extract_key_quotes(video_id, understanding, segment_type)

        result.speaker_segments = speaker_segs
        result.key_quotes = quotes
        result.speakers_identified = len(
            {s.speaker_id or s.speaker_name for s in speaker_segs if s.speaker_id or s.speaker_name}
        )
        result.total_duration_seconds = understanding.transcript.duration_covered

        logger.info(
            "[InterviewDetection] video_id=%s quotes=%d speakers=%d",
            video_id,
            len(quotes),
            result.speakers_identified,
        )
        return result

    def _classify_source(self, ingestion: VideoIngestionResult) -> InterviewSegmentType:
        stype = ingestion.source.source_type
        mapping = {
            VideoSourceType.PRESS_CONFERENCE: InterviewSegmentType.PRESS_CONFERENCE,
            VideoSourceType.INTERVIEW: InterviewSegmentType.PLAYER_INTERVIEW,
            VideoSourceType.PODCAST_VIDEO: InterviewSegmentType.PUNDIT_ANALYSIS,
        }
        return mapping.get(stype, InterviewSegmentType.UNKNOWN)

    def _extract_speaker_segments(
        self, video_id: str, understanding: VideoUnderstandingResult
    ) -> list[SpeakerSegment]:
        if not understanding.transcript:
            return []
        return [
            SpeakerSegment(
                start_seconds=seg.start_seconds,
                end_seconds=seg.end_seconds,
                text=seg.text,
                speaker_id=seg.speaker or "",
                language=seg.language,
            )
            for seg in understanding.transcript.segments
            if seg.text.strip()
        ]

    async def _extract_key_quotes(
        self,
        video_id: str,
        understanding: VideoUnderstandingResult,
        segment_type: InterviewSegmentType,
    ) -> list[KeyQuote]:
        if not understanding.transcript:
            return []

        quotes: list[KeyQuote] = []

        # AI-based extraction
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                excerpt = understanding.transcript.full_text[:1500]
                response = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            "Extract the 3 most newsworthy quotes from this sports "
                            f"interview transcript. Type: {segment_type.value}. "
                            "Format each quote as: START_SEC|END_SEC|SPEAKER|QUOTE\n"
                            f"Transcript: {excerpt}"
                        ),
                        max_tokens=300,
                    )
                )
                quotes = self._parse_ai_quotes(video_id, response.content)
            except Exception:
                pass

        # Fallback: rule-based extraction for long segments
        if not quotes:
            quotes = self._rule_based_quotes(video_id, understanding)

        for q in quotes:
            q.topics = self._classify_topics(q.text)
            q.sentiment = self._classify_sentiment(q.text)

        return quotes

    def _parse_ai_quotes(self, video_id: str, raw: str) -> list[KeyQuote]:
        quotes = []
        for line in raw.strip().splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                try:
                    start = float(parts[0].strip())
                    end = float(parts[1].strip())
                    speaker = parts[2].strip()
                    text = parts[3].strip()
                    quotes.append(
                        KeyQuote(
                            video_id=video_id,
                            start_seconds=start,
                            end_seconds=end,
                            speaker_name=speaker,
                            text=text,
                            importance_score=75.0,
                            metadata={"source": "ai"},
                        )
                    )
                except (ValueError, IndexError):
                    continue
        return quotes

    def _rule_based_quotes(
        self, video_id: str, understanding: VideoUnderstandingResult
    ) -> list[KeyQuote]:
        if not understanding.transcript:
            return []
        # Pick segments longer than 10 words as candidate quotes
        quotes = []
        for seg in understanding.transcript.segments:
            if len(seg.text.split()) >= 10:
                quotes.append(
                    KeyQuote(
                        video_id=video_id,
                        start_seconds=seg.start_seconds,
                        end_seconds=seg.end_seconds,
                        text=seg.text,
                        speaker_name=seg.speaker or "",
                        importance_score=60.0,
                        metadata={"source": "rule_based"},
                    )
                )
        return quotes[:5]

    def _classify_topics(self, text: str) -> list[str]:
        text_lower = text.lower()
        return [
            topic
            for topic, keywords in _TOPIC_KEYWORDS.items()
            if any(kw in text_lower for kw in keywords)
        ]

    def _classify_sentiment(self, text: str) -> str:
        text_lower = text.lower()
        positive = ["great", "excellent", "happy", "proud", "رائع", "سعيد", "فخور"]
        negative = ["difficult", "hard", "disappointing", "صعب", "خيبة", "مستأت"]
        if any(w in text_lower for w in positive):
            return "positive"
        if any(w in text_lower for w in negative):
            return "negative"
        return "neutral"

    def _dry_run_content(
        self, video_id: str
    ) -> tuple[list[SpeakerSegment], list[KeyQuote]]:
        speaker = SpeakerSegment(
            start_seconds=0.0,
            end_seconds=60.0,
            speaker_name="[DRY RUN] Coach",
            speaker_role="coach",
            text="[DRY RUN] نحن نعمل بجد لتحقيق الفوز في كل مباراة.",
            language="arabic",
        )
        quote = KeyQuote(
            video_id=video_id,
            start_seconds=5.0,
            end_seconds=20.0,
            text="[DRY RUN] نحن نعمل بجد لتحقيق الفوز في كل مباراة.",
            speaker_name="Coach",
            speaker_role="coach",
            importance_score=80.0,
            topics=["performance", "ambition"],
            sentiment="positive",
            metadata={"dry_run": True},
        )
        return [speaker], [quote]
