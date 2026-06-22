"""AI Image Factory models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ImageProvider(str, Enum):
    GPT_IMAGE = "gpt_image"
    FLUX = "flux"
    IDEOGRAM = "ideogram"
    MIDJOURNEY = "midjourney"


class ImageFormat(str, Enum):
    PLAYER_POSTER = "player_poster"
    MATCH_POSTER = "match_poster"
    LINEUP = "lineup"
    COVER_IMAGE = "cover_image"
    SOCIAL_CARD = "social_card"
    INFOGRAPHIC = "infographic"
    SPONSOR_ASSET = "sponsor_asset"


class ImageDimension(str, Enum):
    SQUARE = "1080x1080"
    PORTRAIT = "1080x1350"
    STORY = "1080x1920"
    LANDSCAPE = "1280x720"
    COVER = "1584x396"


class ImageVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid4()))
    variant_label: str = "v1"
    provider: ImageProvider = ImageProvider.FLUX
    prompt_used: str = ""
    negative_prompt: str = ""
    file_url: str = ""
    dimensions: ImageDimension = ImageDimension.SQUARE
    style: str = ""
    quality_score: float = 0.0
    brand_alignment_score: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ImageAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    image_format: ImageFormat
    title: str
    subject: str = ""
    platform: str = ""
    variants: list[ImageVariant] = Field(default_factory=list)
    primary_variant_id: str = ""
    brand_alignment_score: float = 0.0
    prompt_library: list[str] = Field(default_factory=list)
    style_guide_applied: bool = True
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[{self.image_format.value}] '{self.title}' — "
            f"{len(self.variants)} variant(s), brand alignment: {self.brand_alignment_score:.0f}/100."
        )


class ImageGenerationReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    assets: list[ImageAsset] = Field(default_factory=list)
    total_generated: int = 0
    total_variants: int = 0
    avg_brand_alignment: float = 0.0
    providers_used: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
