# Package 8E — Creative Production Layer

## Overview

Package 8E transforms SFC from an intelligence platform into an **autonomous multimedia production company**. It takes intelligence outputs from Packages 8B/8C/8D and produces platform-ready media assets at scale — images, videos, thumbnails, audio, shorts, and podcasts — all in one LangGraph pipeline.

---

## Architecture

```
src/sfc/creative/
├── orchestrator/    Creative Production Orchestrator
├── image/           AI Image Factory
├── video/           AI Video Factory
├── thumbnail/       AI Thumbnail Factory (A/B/C/D CTR variants)
├── audio/           AI Audio Factory
├── shorts/          AI Shorts Factory
├── podcast/         AI Podcast Factory
├── assets/          Creative Asset Management
├── quality/         Production Quality Control
└── packaging/       Content Packaging Engine
```

Each component has:
- `models.py` — Pydantic v2 data models
- `service.py` — Singleton async service

---

## LangGraph Pipeline

```
START
  → creative_production    Build production plan from intelligence
  → image_factory          GPT Image / Flux / Ideogram (mocked)
  → video_factory          Google Veo / Kling / Runway (mocked)
  → thumbnail_factory      A/B/C/D CTR-optimised variants
  → audio_factory          ElevenLabs / Azure Voice (mocked)
  → shorts_factory         TikTok / Reels / YouTube Shorts
  → podcast_factory        Full episode + segments + chapters
  → asset_management       Registry + lifecycle tracking
  → quality_control        5-point brand/QC checks
  → content_packaging      Platform-ready bundles
END
```

Graph location: `src/sfc/graph/creative_production_graph.py`

```python
from sfc.graph.creative_production_graph import build_creative_production_graph

graph = build_creative_production_graph()
result = await graph.ainvoke(state)
```

---

## Components

### 1. Creative Production Orchestrator

Reads social intelligence state (narratives, trends, war room status) and builds a `ProductionPlan` listing which formats to produce and which personas to assign.

**Triggers**: `NARRATIVE`, `TREND`, `WAR_ROOM`, `SCHEDULED`, `OPPORTUNITY`, `EXECUTIVE`

**Priorities**: `URGENT` (war room active) → `HIGH` → `NORMAL` → `LOW`

### 2. AI Image Factory

Generates branded images with multiple variants per asset. All providers mocked.

- Formats: `PLAYER_POSTER`, `MATCH_POSTER`, `LINEUP`, `COVER_IMAGE`, `SOCIAL_CARD`, `INFOGRAPHIC`, `SPONSOR_ASSET`
- Providers: GPT Image, Flux, Ideogram, Midjourney
- Dimensions: SQUARE (1080×1080), PORTRAIT (1080×1350), STORY (1080×1920), LANDSCAPE, COVER

### 3. AI Video Factory

Generates short-form and long-form video with storyboard.

- Formats: SHORT (60s), REEL (30s), TIKTOK (45s), MATCH_STORY (90s), DOCUMENTARY (300s)
- Providers: Google Veo, Kling, Runway, Luma, Pika
- Aspect ratios: 9:16 (vertical), 1:1 (square), 16:9 (horizontal)

### 4. AI Thumbnail Factory

Generates 4 A/B/C/D variants per video with CTR prediction scores.

- Each variant has: CTR score, curiosity score, brand alignment, click probability, emotional hook
- Styles: bold_text_yellow, dramatic_face_close_up, action_freeze_frame, minimal_clean
- AI recommendation selects winner based on predicted CTR

### 5. AI Audio Factory

Generates Arabic and English voice content.

- Types: `NARRATION`, `MATCH_RECAP`, `NEWS_BRIEF`, `SPONSOR_READ`, `PODCAST_SEGMENT`, `INTRO_JINGLE`
- Providers: ElevenLabs, Azure Voice, OpenAI Voice
- Duration auto-calculated from word count and language WPM (Arabic: 140 WPM, English: 160 WPM)

### 6. AI Shorts Factory

Generates complete short-form packages for all platforms simultaneously.

- Platforms: YouTube Shorts, TikTok, Instagram Reels
- Each package: hook + body + CTA script, storyboard scenes, hashtags, caption, music suggestion
- Platform-specific hashtag counts (YT: 5, TikTok: 8, Instagram: 12)

### 7. AI Podcast Factory

Generates full podcast episodes with segments, chapters, show notes.

- Types: `DAILY_SHOW`, `MATCH_RECAP`, `TRANSFER_SHOW`, `WORLD_CUP_SHOW`, `TACTICAL_SHOW`
- Segments: INTRO + CONTENT + ANALYSIS + INTERVIEW (optional) + SPONSOR + OUTRO
- Total duration: 18–40 minutes depending on type
- Episode numbers auto-increment per podcast type

### 8. Creative Asset Management

Central registry for all produced assets with lifecycle tracking.

- Statuses: `PENDING` → `GENERATING` → `GENERATED` → `QC_PENDING` → `APPROVED` / `REJECTED` → `PUBLISHED`
- Registry report: count by type, count by status, avg quality score
- Helper methods: `register_image_asset()`, `register_video_asset()`, `register_shorts_package()`, `register_podcast_episode()`

### 9. Production Quality Control

Runs 5 quality checks on every asset before packaging.

| Check Type | What it verifies |
|---|---|
| BRAND_ALIGNMENT | SFC brand colors, style guide compliance |
| VISUAL_QUALITY | Resolution, sharpness, production standard |
| NARRATIVE_CONSISTENCY | Tone, messaging alignment with SFC voice |
| GOVERNANCE_COMPLIANCE | Constitutional and editorial policy compliance |
| TECHNICAL_QUALITY | File format, encoding, platform spec compliance |

- Approval threshold: overall score ≥ 70
- Warn threshold: 55–69
- Fail: < 55

### 10. Content Packaging Engine

Assembles platform-ready content bundles with metadata.

- Package types: `X_THREAD`, `YOUTUBE_SHORT`, `YOUTUBE_VIDEO`, `INSTAGRAM`, `TIKTOK`, `PODCAST`
- Each package: title, description, caption, hashtags, thumbnail URL, media assets, publishing metadata
- `ready_to_publish` only set when `quality_score ≥ 70` AND `governance_cleared = True`

---

## State Keys Added

| Key | Type | Description |
|---|---|---|
| `production_plan` | `dict` | Production plan from orchestrator |
| `image_assets` | `list[dict]` | Generated image assets |
| `video_assets` | `list[dict]` | Generated video assets |
| `thumbnail_assets` | `list[dict]` | Thumbnail sets with CTR predictions |
| `audio_assets` | `list[dict]` | Voice/audio assets |
| `shorts_packages` | `list[dict]` | Short-form video packages |
| `podcast_episodes` | `list[dict]` | Full podcast episodes |
| `asset_registry` | `dict` | Asset management registry report |
| `quality_reports` | `list[dict]` | Per-asset QC reports |
| `content_packages` | `list[dict]` | Platform-ready content bundles |

---

## Events Added

| Event Type | Trigger |
|---|---|
| `production_plan_created` | Orchestrator builds plan |
| `image_assets_generated` | Image factory completes |
| `video_assets_generated` | Video factory completes |
| `shorts_package_generated` | Shorts factory completes |
| `podcast_episode_generated` | Podcast factory completes |
| `quality_review_completed` | QC batch finishes |
| `content_package_ready` | Package assembled |
| `creative_production_completed` | Full pipeline done |

---

## Governance

All packages produced by this layer have:
- `publishing_metadata.requires_approval = True`
- `governance_cleared = False` (set only by main pipeline governance gate)
- `ready_to_publish = False` until both quality and governance conditions met

**No content is published from this pipeline.** All packages route through the main pipeline (`graph.py`) governance gate before any publishing action.

---

## Tests

```bash
# Unit tests
pytest tests/creative/ -v

# Integration tests
pytest tests/integration/test_pkg8e_e2e.py -v
```

Test coverage: 91 unit tests + 54 integration tests = **145 tests total**
