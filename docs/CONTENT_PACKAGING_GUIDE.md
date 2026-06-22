# Content Packaging Engine Guide

## Overview

The Content Packaging Engine assembles all produced creative assets into platform-ready bundles. It applies publishing metadata, validates quality and governance clearance, and determines publishing readiness. No content is published until `quality_score ≥ 70` AND `governance_cleared = True`.

## Quick Start

```python
from sfc.creative.packaging.service import get_content_packaging_service
from sfc.creative.packaging.models import PackageType

service = get_content_packaging_service()

# Create a package manually
pkg = await service.create_package(
    package_type=PackageType.YOUTUBE_SHORT,
    title="SPL Round 10 Best Goals",
    description="Top goals from round 10 of the Saudi Pro League",
    quality_score=85.0,
    governance_cleared=True,   # Set by governance gate
    thumbnail_url="https://assets.sfc.sa/thumbnails/r10.jpg",
    media_assets=[video_asset.to_dict()],
)

print(pkg.to_summary())
# [youtube_short] 'SPL Round 10 Best Goals' [READY] — quality: 85/100, 5 hashtags.

# Create from asset objects
pkg = await service.package_from_assets(
    package_type=PackageType.TIKTOK,
    title="Transfer Deadline Day",
    assets=[shorts_pkg, image_asset],
    quality_score=78.0,
    governance_cleared=True,
)
```

## Publishing Readiness

A package is `ready_to_publish = True` only when **both** conditions are met:

```python
quality_score >= 70.0  AND  governance_cleared = True
```

```python
# Mark governance cleared after governance gate approves
service.mark_governance_cleared(package_id=pkg.package_id)
# → pkg.ready_to_publish is now True (if quality_score >= 70)
```

## Package Types

| Type | Platform | Default Hashtags |
|---|---|---|
| `X_THREAD` | X (Twitter) | #SFC, #SaudiFootball, #Thread, #SPL |
| `YOUTUBE_SHORT` | YouTube | #SFC, #SaudiFootball, #Shorts, #Football |
| `YOUTUBE_VIDEO` | YouTube | #SFC, #SaudiFootball, #YouTube, #SPL |
| `INSTAGRAM` | Instagram | #SFC, #SaudiFootball, #Reels, #Football |
| `TIKTOK` | TikTok | #SFC, #SaudiFootball, #TikTok, #Football, #viral |
| `PODCAST` | Spotify | #SFC, #SaudiFootball, #Podcast, #SportsRadio |

## Publishing Metadata

Every package carries full publishing metadata:

```python
pkg.publishing_metadata.platform          # "youtube", "tiktok", etc.
pkg.publishing_metadata.language          # "arabic" (default)
pkg.publishing_metadata.requires_approval # True (always)
pkg.publishing_metadata.category          # "sports"
pkg.publishing_metadata.target_audience   # "Saudi football fans"
pkg.publishing_metadata.geo_targeting     # ["SA", "AE", "QA", "KW"]
pkg.publishing_metadata.boost_budget_usd  # 0.0 (set by scheduler)
pkg.publishing_metadata.scheduled_at      # None (set by scheduler)
```

## Packaging Report

```python
report = await service.generate_packaging_report()

print(f"Total packages: {report.total_packages}")
print(f"Ready to publish: {report.ready_to_publish}")
print(f"By type: {report.packages_by_type}")
print(f"Avg quality: {report.avg_quality_score:.0f}/100")
```

## Getting Ready Packages

```python
ready = service.get_ready_packages()
for pkg in ready:
    print(f"{pkg.package_type.value}: {pkg.title}")
```

## Governance Contract

The packaging layer enforces these constraints:

1. `requires_approval` is **always** `True` on `PublishingMetadata`
2. `governance_cleared` starts as `False` — must be explicitly set
3. `ready_to_publish` is computed, never set directly
4. The packaging engine never calls publishing or governance services

Packages are handed off to the main pipeline's governance gate via the `content_packages` state key.

## Data Model

```python
class ContentPackage:
    package_id: str
    package_type: PackageType
    title: str
    description: str
    caption: str
    hashtags: list[str]
    thumbnail_url: str
    media_asset_ids: list[str]
    media_assets: list[dict]
    publishing_metadata: PublishingMetadata
    quality_score: float
    ready_to_publish: bool         # computed
    governance_cleared: bool
    generated_at: datetime

class PublishingMetadata:
    platform: str
    scheduled_at: datetime | None
    target_audience: str
    boost_budget_usd: float
    geo_targeting: list[str]
    language: str                  # "arabic"
    requires_approval: bool        # always True
    category: str
```
