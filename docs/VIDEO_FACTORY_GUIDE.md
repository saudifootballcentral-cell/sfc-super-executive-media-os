# AI Video Factory Guide

## Overview

The AI Video Factory generates short-form and long-form football video content with full storyboards. It selects the appropriate AI provider, aspect ratio, and duration based on format and platform.

## Quick Start

```python
from sfc.creative.video.service import get_video_factory_service
from sfc.creative.video.models import VideoFormat

service = get_video_factory_service()

asset = await service.generate_video(
    title="Al Nassr Goal of the Season",
    video_format=VideoFormat.SHORT,
    platform="youtube",
    narrative="Ronaldo overhead kick in the 90th minute",
)

print(asset.to_summary())
# [short] 'Al Nassr Goal of the Season' — 60s 9:16, provider: kling.

print(f"Scenes: {asset.storyboard.total_scenes}")
print(f"Brand alignment: {asset.brand_alignment_score:.0f}/100")
```

## Video Formats

| Format | Duration | Default Aspect |
|---|---|---|
| `SHORT` | 60s | 9:16 (vertical) |
| `REEL` | 30s | 9:16 (vertical) |
| `TIKTOK` | 45s | 9:16 (vertical) |
| `MATCH_STORY` | 90s | 9:16 (vertical) |
| `PLAYER_STORY` | 60s | 9:16 (vertical) |
| `TRANSFER_STORY` | 75s | 9:16 (vertical) |
| `DOCUMENTARY_SEGMENT` | 300s | 16:9 (horizontal) |
| `NARRATIVE_VIDEO` | 180s | 16:9 (horizontal) |

## Storyboard

Every video asset includes a machine-readable storyboard:

```python
for scene in asset.storyboard.scenes:
    print(f"Scene {scene.scene_id}: {scene.visual_description}")
    print(f"  Audio: {scene.audio_direction}")
    print(f"  Duration: {scene.duration_seconds}s")
    print(f"  Transition: {scene.transition}")
    if scene.b_roll:
        print(f"  B-Roll: {scene.b_roll}")
```

## Providers

| Provider | Best For |
|---|---|
| `GOOGLE_VEO` | Long-form, documentary |
| `KLING` | Sports highlights, fast action |
| `RUNWAY` | Cinematic, narrative |
| `LUMA` | Story-driven, emotional |
| `PIKA` | Short viral clips |

## Batch Generation

```python
report = await service.generate_batch(
    titles=["Matchday Highlights", "Player Spotlight", "Transfer News"],
    video_format=VideoFormat.SHORT,
    platform="youtube",
)

print(f"Generated: {report.total_generated}")
print(f"Total duration: {report.total_duration_seconds:.0f}s")
print(f"Providers: {report.providers_used}")
```

## Platform Selection

The service automatically selects aspect ratio based on platform:

- `tiktok`, `instagram` → 9:16 (VERTICAL)
- `youtube` + short format → 9:16 (VERTICAL)
- `youtube` + long format → 16:9 (HORIZONTAL)

## Data Model

```python
class VideoAsset:
    asset_id: str
    video_format: VideoFormat
    title: str
    provider: VideoProvider
    duration_seconds: float
    aspect_ratio: AspectRatio
    file_url: str
    storyboard: Storyboard
    prompt_used: str
    platform: str
    brand_alignment_score: float
    estimated_completion_rate: float  # predicted viewer retention %
    generated_at: datetime

class Storyboard:
    storyboard_id: str
    title: str
    total_scenes: int
    total_duration_seconds: float
    aspect_ratio: AspectRatio
    scenes: list[StoryboardScene]
    music_direction: str
    color_grade: str
```
