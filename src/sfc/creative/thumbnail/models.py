"""AI Thumbnail Factory models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ThumbnailVariantLabel(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class CTRPrediction(BaseModel):
    ctr_score: float = 0.0
    curiosity_score: float = 0.0
    brand_alignment: float = 0.0
    click_probability: float = 0.0
    emotional_hook: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ThumbnailVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid4()))
    label: ThumbnailVariantLabel
    title_text: str = ""
    visual_style: str = ""
    color_scheme: str = ""
    file_url: str = ""
    prompt_used: str = ""
    ctr_prediction: CTRPrediction = Field(default_factory=CTRPrediction)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ThumbnailAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    content_title: str
    platform: str = ""
    variants: list[ThumbnailVariant] = Field(default_factory=list)
    recommended_variant: ThumbnailVariantLabel | None = None
    best_ctr_score: float = 0.0
    best_curiosity_score: float = 0.0
    ai_recommendation: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"Thumbnail '{self.content_title}' — {len(self.variants)} variants, "
            f"best CTR: {self.best_ctr_score:.0f}/100, "
            f"recommended: variant {self.recommended_variant}."
        )
