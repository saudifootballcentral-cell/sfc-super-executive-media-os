# AI Image Factory Guide

## Overview

The AI Image Factory generates branded Saudi football imagery across all formats and platforms. Every image is produced as multiple variants with quality and brand alignment scores.

## Quick Start

```python
from sfc.creative.image.service import get_image_factory_service
from sfc.creative.image.models import ImageFormat

service = get_image_factory_service()

# Generate a single image with 2 variants
asset = await service.generate_image(
    title="Al Hilal vs Al Nassr Derby",
    subject="Al Hilal",
    image_format=ImageFormat.MATCH_POSTER,
    platform="instagram",
    num_variants=2,
)

print(asset.to_summary())
# [match_poster] 'Al Hilal vs Al Nassr Derby' — 2 variant(s), brand alignment: 91/100.

# Best variant
primary = next(v for v in asset.variants if v.variant_id == asset.primary_variant_id)
print(primary.file_url)
```

## Image Formats

| Format | Use Case | Default Dimension |
|---|---|---|
| `PLAYER_POSTER` | Player feature, spotlight | PORTRAIT (1080×1350) |
| `MATCH_POSTER` | Match day promotion | LANDSCAPE (1280×720) |
| `LINEUP` | Team lineup graphic | SQUARE (1080×1080) |
| `COVER_IMAGE` | Channel/profile cover | COVER (1584×396) |
| `SOCIAL_CARD` | General social post | SQUARE (1080×1080) |
| `INFOGRAPHIC` | Stats, data viz | SQUARE (1080×1080) |
| `SPONSOR_ASSET` | Sponsor integration | LANDSCAPE (1280×720) |

## Batch Generation

```python
report = await service.generate_batch(
    subjects=["Al Hilal", "Al Nassr", "Al Ittihad"],
    image_format=ImageFormat.PLAYER_POSTER,
    platform="instagram",
)

print(f"Generated: {report.total_generated} assets")
print(f"Total variants: {report.total_variants}")
print(f"Avg brand alignment: {report.avg_brand_alignment:.0f}/100")
print(f"Providers used: {report.providers_used}")
```

## Providers

All providers are mocked — no credentials required.

| Provider | Style |
|---|---|
| `FLUX` | Photorealistic, high detail |
| `IDEOGRAM` | Typography-aware |
| `GPT_IMAGE` | Creative, narrative |
| `MIDJOURNEY` | Artistic, cinematic |

## Prompt Library

The service maintains a prompt library per asset. Access past prompts for consistency:

```python
asset = await service.generate_image(title="Player Feature")
for prompt in asset.prompt_library:
    print(prompt)
```

## Style Guide

All images are generated with the SFC style guide applied:
- Saudi football aesthetic
- SFC brand colors: green / gold / white
- High contrast for social feeds
- Arabic typography compatible
- Premium sports editorial feel

`asset.style_guide_applied` will always be `True` from this service.

## Data Model

```python
class ImageAsset:
    asset_id: str
    image_format: ImageFormat
    title: str
    subject: str
    platform: str
    variants: list[ImageVariant]
    primary_variant_id: str
    brand_alignment_score: float      # avg across variants
    prompt_library: list[str]
    style_guide_applied: bool
    generated_at: datetime

class ImageVariant:
    variant_id: str
    variant_label: str                # "v1", "v2", ...
    provider: ImageProvider
    prompt_used: str
    negative_prompt: str
    file_url: str
    dimensions: ImageDimension
    style: str
    quality_score: float              # 0–100
    brand_alignment_score: float      # 0–100
```
