"""Clip Scoring Engine — viral potential, audience appeal, brand alignment."""

from __future__ import annotations

import logging
import random

from sfc.video_intelligence.clipping.models import ClipSourceType, VideoClip
from sfc.video_intelligence.event_detection.models import SportEventType
from sfc.video_intelligence.shared.constants import PLATFORM_MAX_DURATION
from sfc.video_intelligence.scoring.models import ClipScore, PlatformScore

logger = logging.getLogger("sfc.video_intelligence.scoring")

_singleton: "ClipScoringEngine | None" = None

# Clip type → base viral score
_TYPE_VIRAL_BASE: dict[str, float] = {
    "goal": 92.0,
    "save": 82.0,
    "penalty": 85.0,
    "red_card": 75.0,
    "var_review": 70.0,
    "skill": 80.0,
    "celebration": 78.0,
    "controversial": 73.0,
    "near_miss": 65.0,
    "key_quote": 68.0,
    "highlight": 72.0,
}


def get_clip_scoring_engine() -> "ClipScoringEngine":
    global _singleton
    if _singleton is None:
        _singleton = ClipScoringEngine()
    return _singleton


class ClipScoringEngine:
    """Scores each clip across viral potential, appeal, brand, and platform fit."""

    async def score(self, clip: VideoClip) -> ClipScore:
        viral = self._score_viral(clip)
        appeal = self._score_audience_appeal(clip)
        brand = self._score_brand_alignment(clip)
        technical = self._score_technical_quality(clip)
        overall = round((viral * 0.35 + appeal * 0.25 + brand * 0.25 + technical * 0.15), 1)

        platform_scores = [
            self._platform_score(platform, clip, viral)
            for platform in PLATFORM_MAX_DURATION
        ]
        platform_scores.sort(key=lambda p: p.suitability_score, reverse=True)
        best = platform_scores[0].platform if platform_scores else ""

        score = ClipScore(
            clip_id=clip.clip_id,
            viral_potential=viral,
            audience_appeal=appeal,
            brand_alignment=brand,
            technical_quality=technical,
            overall_score=overall,
            platform_scores=platform_scores,
            best_platform=best,
            recommended_clip_length=self._recommend_length(clip, best),
        )
        logger.debug(
            "[Scoring] clip_id=%s overall=%.1f best_platform=%s",
            clip.clip_id, overall, best,
        )
        return score

    def _score_viral(self, clip: VideoClip) -> float:
        base = _TYPE_VIRAL_BASE.get(clip.clip_type, 65.0)
        # Duration factor — 30-60s is the sweet spot
        dur = clip.duration_seconds
        if 20 <= dur <= 60:
            dur_bonus = 5.0
        elif dur < 10 or dur > 120:
            dur_bonus = -10.0
        else:
            dur_bonus = 0.0
        return min(100.0, round(base + dur_bonus + random.uniform(-3, 3), 1))

    def _score_audience_appeal(self, clip: VideoClip) -> float:
        if clip.source_type == ClipSourceType.SPORT_EVENT:
            base = 80.0
        elif clip.source_type == ClipSourceType.KEY_QUOTE:
            base = 70.0
        else:
            base = 68.0
        return min(100.0, round(base + random.uniform(-5, 5), 1))

    def _score_brand_alignment(self, clip: VideoClip) -> float:
        # All SFC clips default to high brand alignment
        base = 82.0
        if clip.clip_type in ("controversial",):
            base = 62.0
        return min(100.0, round(base + random.uniform(-4, 4), 1))

    def _score_technical_quality(self, clip: VideoClip) -> float:
        if clip.file_size_bytes > 0:
            return 88.0
        if clip.status.value == "dry_run":
            return 80.0
        return 72.0

    def _platform_score(
        self, platform: str, clip: VideoClip, viral: float
    ) -> PlatformScore:
        max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
        within = clip.duration_seconds <= max_dur
        ratio = min(1.0, clip.duration_seconds / max(max_dur, 1)) if within else 0.5
        suitability = round(viral * ratio * (0.95 if within else 0.6), 1)
        aspect = "16:9"
        if platform in ("youtube_short", "instagram_reel", "tiktok"):
            aspect = "9:16"
        return PlatformScore(
            platform=platform,
            suitability_score=min(100.0, suitability),
            recommended_format=aspect,
            max_duration_seconds=float(max_dur),
            within_duration_limit=within,
        )

    def _recommend_length(self, clip: VideoClip, platform: str) -> float:
        max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
        return min(float(max_dur), clip.duration_seconds)
