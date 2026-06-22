# Package 10E — Video Intelligence & Smart Clip Extraction

## Overview

Package 10E adds a 12-stage Video Intelligence pipeline that ingests videos,
detects high-value moments, extracts publishable clips, applies governance,
and routes them to the existing publishing pipeline.

**No existing packages are rebuilt.** The Creative Production Layer, Content
Packaging Engine, and Publishing pipeline are extended, not replaced.

---

## Module Layout

```
src/sfc/video_intelligence/
    ingestion/          ← Stage 1: Video source validation & metadata extraction
    understanding/      ← Stage 2: Transcription, scene detection, frame indexing
    event_detection/    ← Stage 3: Sport event detection (goal, save, penalty…)
    interview_detection/← Stage 4: Press conference & interview segment detection
    clipping/           ← Stage 5: Smart clip extraction from detected events
    scoring/            ← Stage 6: Viral potential, audience appeal, platform fit
    enhancement/        ← Stage 7: Aspect ratio variants per platform
    captioning/         ← Stage 8: SRT subtitle generation (Arabic + English)
    packaging/          ← Stage 9: ClipPackage assembly with platform metadata
    governance/         ← Stage 10: Rights, brand safety, content policy gate
    publishing/         ← Stage 11: Routes to ContentPackagingService
    learning/           ← Stage 12: Engagement tracking & weight adjustment
    shared/             ← Constants and environment variable helpers
    orchestrator.py     ← Ties all 12 stages into a single pipeline call
```

---

## 12-Stage Pipeline

| # | Stage | Service | Key Output |
|---|-------|---------|-----------|
| 1 | Ingestion | `VideoIngestionService` | `VideoIngestionResult` |
| 2 | Understanding | `VideoUnderstandingService` | `VideoUnderstandingResult` (transcript, scenes) |
| 3 | Sport Event Detection | `SportEventDetectionService` | `EventDetectionResult` |
| 4 | Interview Detection | `InterviewDetectionService` | `InterviewDetectionResult` (quotes) |
| 5 | Smart Clipping | `SmartClippingEngine` | `list[VideoClip]` |
| 6 | Scoring | `ClipScoringEngine` | `ClipScore` |
| 7 | Enhancement | `ClipEnhancementEngine` | `EnhancementResult` (platform variants) |
| 8 | Captioning | `AutoCaptioningEngine` | `CaptioningResult` (SRT tracks) |
| 9 | Packaging | `ClipPackagingEngine` | `ClipPackage` |
| 10 | Governance | `ClipGovernanceLayer` | `ClipGovernanceResult` |
| 11 | Publishing | `ClipPublishingIntegration` | Routes to `ContentPackagingService` |
| 12 | Learning | `ClipLearningLoop` | `ClipPerformanceRecord` |

---

## Detected Event Types

`SportEventType`: goal, save, skill, celebration, tactical_moment, controversial,
near_miss, red_card, yellow_card, injury, substitution, penalty, free_kick,
corner, var_review, crowd_reaction, coach_reaction

`InterviewSegmentType`: player_interview, coach_interview, press_conference,
pundit_analysis, fan_interview

---

## Entry Point

```python
import asyncio
from sfc.video_intelligence.orchestrator import get_video_intelligence_orchestrator
from sfc.video_intelligence.ingestion.models import VideoSource, VideoSourceType, RightsStatus

orch = get_video_intelligence_orchestrator()
source = VideoSource(
    source_type=VideoSourceType.MATCH_RECORDING,
    title="SPL Match — Al-Hilal vs Al-Nassr",
    path="/media/matches/match_2026.mp4",
    rights_status=RightsStatus.OWNED,
)
result = asyncio.run(orch.process_video(source))
print(result.summary())
# → [VideoIntelligence] run_id=... status=OK clips=4 published=3
```

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `VIDEO_PROCESSING_ENABLED` | `false` | Master switch — set to `true` for real processing |
| `VIDEO_STORAGE_PATH` | `./artifacts/video` | Root for video artifacts |
| `VIDEO_CLIP_STORAGE_PATH` | `./artifacts/video/clips` | Root for clip files |
| `VIDEO_WHISPER_API_KEY` | `OPENAI_API_KEY` fallback | OpenAI Whisper transcription |
| `VIDEO_FRAME_SAMPLE_RATE` | `1.0` | Frames per second to sample |
| `VIDEO_MIN_CLIP_DURATION` | `5` | Minimum clip duration (seconds) |
| `VIDEO_MAX_CLIP_DURATION` | `90` | Maximum clip duration (seconds) |
| `VIDEO_CLIP_QUALITY_THRESHOLD` | `70.0` | Minimum quality score for governance |

---

## Safe Default

When `VIDEO_PROCESSING_ENABLED=false` (default):
- No video files are read or processed
- No API calls are made
- All services return dry-run/planning results
- Full pipeline runs without cost or risk

When `VIDEO_PROCESSING_ENABLED=true`:
- `ffprobe` used for metadata extraction (if available)
- `ffmpeg` used for clip extraction and aspect ratio conversion (if available)
- OpenAI Whisper API used for transcription (if `VIDEO_WHISPER_API_KEY` set)
- AI gateway used for event analysis and caption translation
