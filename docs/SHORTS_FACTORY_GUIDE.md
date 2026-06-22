# AI Shorts Factory Guide

## Overview

The AI Shorts Factory generates complete short-form video packages for TikTok, Instagram Reels, and YouTube Shorts. Each package includes a full script (hook + body + CTA), storyboard scenes, platform-specific hashtags, caption, and music suggestion.

## Quick Start

```python
from sfc.creative.shorts.service import get_shorts_factory_service
from sfc.creative.shorts.models import ShortsPlatform

service = get_shorts_factory_service()

# Single platform
pkg = await service.generate_shorts_package(
    title="SPL Round 10 Best Goals",
    platform=ShortsPlatform.TIKTOK,
    narrative="Explosive goals from round 10",
    subject="SPL Goals",
)

print(pkg.to_summary())
# Shorts 'SPL Round 10 Best Goals' [tiktok] — 45s, 8 hashtags, 9 scenes.

# All 3 platforms at once
packages = await service.generate_multi_platform(
    title="Transfer Deadline Day",
    narrative="Last-minute Saudi Pro League transfer",
)
# Returns 3 packages: YouTube Shorts, TikTok, Instagram Reels
```

## Package Contents

```python
pkg.script.hook           # Opening 5-second hook
pkg.script.body           # Main content script
pkg.script.call_to_action # Closing CTA
pkg.script.full_script    # Complete assembled script
pkg.storyboard            # list[ShortsScene] — visual breakdown
pkg.caption               # Platform caption with emoji
pkg.hashtags              # Platform-appropriate hashtag list
pkg.duration_seconds      # Target duration
pkg.music_suggestion      # Music direction
pkg.voiceover_plan        # Arabic voiceover briefing
pkg.visual_plan           # Visual direction note
```

## Platform Defaults

| Platform | Duration | Hashtag Count |
|---|---|---|
| `YOUTUBE_SHORTS` | 58s | 5 |
| `TIKTOK` | 45s | 8 |
| `INSTAGRAM_REELS` | 30s | 12 |

## Script Structure

Every script follows the viral short-form formula:

1. **Hook** (first 5 seconds) — Arabic question or dramatic statement
2. **Body** (middle) — key narrative content, highlights
3. **Call to Action** (final 5 seconds) — subscribe/follow SFC

## Hashtag Strategy

The service mixes:
- SFC brand hashtags: `#SFC`, `#SaudiFootball`, `#الدوري_السعودي`
- Platform-specific: `#Shorts`, `#TikTok`, `#Reels`
- Subject-specific: derived from the `subject` parameter
- Global football: `#Football`, `#SPL`, `#Soccer`

## Storyboard Scenes

Each scene specifies:

```python
class ShortsScene:
    scene_number: int
    duration_seconds: float
    visual_description: str   # Shot description
    text_overlay: str         # On-screen text
    audio_note: str           # VO or sound direction
```

## Data Model

```python
class ShortsPackage:
    package_id: str
    title: str
    platform: ShortsPlatform
    script: ShortsScript
    storyboard: list[ShortsScene]
    voiceover_plan: str
    visual_plan: str
    thumbnail_url: str
    caption: str
    hashtags: list[str]
    duration_seconds: float
    music_suggestion: str
    publishing_metadata: dict    # requires_approval: True always
    generated_at: datetime
```
