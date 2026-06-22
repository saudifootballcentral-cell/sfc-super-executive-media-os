# AI Podcast Factory Guide

## Overview

The AI Podcast Factory generates complete, broadcast-quality podcast episodes. Each episode includes a full multi-segment script, chapter markers, show notes, and Spotify-ready publishing metadata. Episode numbers auto-increment per show type.

## Quick Start

```python
from sfc.creative.podcast.service import get_podcast_factory_service
from sfc.creative.podcast.models import PodcastType

service = get_podcast_factory_service()

episode = await service.generate_episode(
    episode_title="SPL Round 10 Recap",
    podcast_type=PodcastType.MATCH_RECAP,
    narratives=[
        "Al Hilal won 3-1 in a dominant display",
        "Ronaldo scored twice in the second half",
        "Al Nassr drops to third place",
    ],
    season=1,
)

print(episode.to_summary())
# [match_recap] 'SPL Round 10 Recap' (EP1) — 4 segments, 20 min.
```

## Podcast Types and Structure

| Type | Segments | Duration |
|---|---|---|
| `DAILY_SHOW` | INTRO + CONTENT + ANALYSIS + SPONSOR + OUTRO | ~18 min |
| `MATCH_RECAP` | INTRO + CONTENT + ANALYSIS + OUTRO | ~20 min |
| `TRANSFER_SHOW` | INTRO + CONTENT + INTERVIEW + ANALYSIS + OUTRO | ~28 min |
| `WORLD_CUP_SHOW` | INTRO + CONTENT + ANALYSIS + INTERVIEW + OUTRO | ~40 min |
| `TACTICAL_SHOW` | INTRO + CONTENT + ANALYSIS + OUTRO | ~25 min |

## Episode Contents

```python
episode.full_script           # Complete assembled script
episode.segments              # list[PodcastSegment]
episode.total_duration_minutes
episode.description           # SEO-ready episode description
episode.show_notes            # Markdown formatted show notes
episode.chapters              # list of chapter dicts with timestamps
episode.tags                  # Spotify/podcast tags
episode.publishing_metadata   # { platform, requires_approval, language, category }
episode.episode_number        # Auto-incremented per podcast_type
```

## Segments

```python
for seg in episode.segments:
    print(f"[{seg.segment_type.value}] {seg.title}")
    print(f"  Duration: {seg.duration_minutes} min")
    print(f"  Speaker: {seg.speaker}")
    print(f"  Talking points: {seg.talking_points}")
    print(f"  Script excerpt: {seg.script[:100]}")
```

## Chapters

The factory auto-builds timestamped chapters:

```python
for chapter in episode.chapters:
    print(f"{chapter['title']}: starts at {chapter['start_time_seconds']}s")
```

## Show Notes Format

Show notes are generated in Markdown and include:
- Per-segment breakdown with duration
- Key talking points per segment
- Topics covered (from narratives)

## Episode Numbering

Episode numbers are tracked per podcast type (reset on service restart):

```python
ep1 = await service.generate_episode("Episode A", PodcastType.DAILY_SHOW)
ep2 = await service.generate_episode("Episode B", PodcastType.DAILY_SHOW)
assert ep2.episode_number == ep1.episode_number + 1  # True
```

## Publishing Metadata

Every episode ships with:
```python
{
    "platform": "spotify",
    "requires_approval": True,    # Always True — awaits governance gate
    "language": "arabic",
    "category": "sports",
}
```

## Data Model

```python
class PodcastEpisode:
    episode_id: str
    podcast_type: PodcastType
    episode_title: str
    episode_number: int
    season: int
    segments: list[PodcastSegment]
    full_script: str
    total_duration_minutes: float
    description: str
    show_notes: str
    chapters: list[dict]
    tags: list[str]
    publishing_metadata: dict
    generated_at: datetime

class PodcastSegment:
    segment_id: str
    segment_number: int
    segment_type: PodcastSegmentType
    title: str
    script: str
    duration_minutes: float
    speaker: str              # "host" or "guest"
    talking_points: list[str]
```
