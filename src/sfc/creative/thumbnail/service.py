"""AI Thumbnail Factory Service — CTR-optimized thumbnails for all platforms."""

from __future__ import annotations

import logging
import os
import random
from typing import Any

from sfc.creative.thumbnail.models import (
    CTRPrediction,
    ThumbnailAsset,
    ThumbnailVariant,
    ThumbnailVariantLabel,
)

logger = logging.getLogger("sfc.creative.thumbnail")

_singleton: "ThumbnailFactoryService | None" = None


def get_thumbnail_factory_service() -> "ThumbnailFactoryService":
    global _singleton
    if _singleton is None:
        _singleton = ThumbnailFactoryService()
    return _singleton


class ThumbnailFactoryService:
    """Generates A/B/C/D thumbnail variants with CTR prediction."""

    _VISUAL_STYLES = [
        "bold_text_yellow",
        "dramatic_face_close_up",
        "action_freeze_frame",
        "minimal_clean",
    ]
    _COLOR_SCHEMES = [
        "green_gold_white",
        "black_gold_contrast",
        "red_urgency",
        "clean_white",
    ]

    def __init__(self) -> None:
        self._gateway = None
        self._assets: list[ThumbnailAsset] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def generate_thumbnails(
        self,
        content_title: str,
        platform: str = "youtube",
        subject: str = "",
        context: dict[str, Any] | None = None,
    ) -> ThumbnailAsset:
        """Generate 4 thumbnail variants (A/B/C/D) with CTR predictions."""
        context = context or {}
        variants = await self._generate_variants(content_title, subject, platform)
        best = max(variants, key=lambda v: v.ctr_prediction.ctr_score)
        ai_rec = await self._generate_recommendation(content_title, variants)

        asset = ThumbnailAsset(
            content_title=content_title,
            platform=platform,
            variants=variants,
            recommended_variant=best.label.value,
            best_ctr_score=best.ctr_prediction.ctr_score,
            best_curiosity_score=best.ctr_prediction.curiosity_score,
            ai_recommendation=ai_rec,
        )
        self._assets.append(asset)
        logger.info(
            "[ThumbnailFactory] Generated | platform=%s best_variant=%s ctr=%.1f",
            platform,
            best.label.value,
            best.ctr_prediction.ctr_score,
        )
        return asset

    async def _generate_variants(
        self,
        title: str,
        subject: str,
        platform: str,
    ) -> list[ThumbnailVariant]:
        labels = list(ThumbnailVariantLabel)
        use_real = os.environ.get("GENERATE_REAL_ASSETS", "false").lower() == "true"
        variants: list[ThumbnailVariant] = []
        for i, label in enumerate(labels):
            style = self._VISUAL_STYLES[i]
            color = self._COLOR_SCHEMES[i]
            prompt = await self._build_prompt(title, subject, style, color)
            ctr = self._predict_ctr(style, platform)
            # Default mock URL for planning / dry-run mode
            file_url = f"https://assets.sfc.sa/thumbnails/mock/{title[:20].replace(' ','_')}_{label.value}.jpg"

            if use_real:
                from sfc.creative.providers.generated_asset import GeneratedAssetStatus
                from sfc.creative.providers.image_providers import get_image_provider_chain
                chain = get_image_provider_chain()
                generated = await chain.generate(
                    prompt=prompt,
                    dimensions="1280x720",
                    negative_prompt="blurry, pixelated, low quality, wrong colors",
                )
                if generated.status == GeneratedAssetStatus.GENERATED:
                    file_url = generated.local_path
                else:
                    file_url = ""

            variants.append(
                ThumbnailVariant(
                    label=label,
                    title_text=self._title_text_for_style(title, style),
                    visual_style=style,
                    color_scheme=color,
                    file_url=file_url,
                    prompt_used=prompt,
                    ctr_prediction=ctr,
                )
            )
        return variants

    def _title_text_for_style(self, title: str, style: str) -> str:
        if style == "bold_text_yellow":
            return title.upper()[:30]
        if style == "minimal_clean":
            return title[:40]
        return title[:35]

    async def _build_prompt(
        self, title: str, subject: str, style: str, color: str
    ) -> str:
        return (
            f"YouTube thumbnail: {subject or title}, {style} style, "
            f"{color} color scheme, SFC Saudi football brand, "
            "high contrast, click-bait worthy, 1280x720"
        )

    def _predict_ctr(self, style: str, platform: str) -> CTRPrediction:
        base_ctr = {
            "bold_text_yellow": 7.2,
            "dramatic_face_close_up": 8.1,
            "action_freeze_frame": 6.8,
            "minimal_clean": 5.5,
        }.get(style, 6.0)
        noise = random.uniform(-0.8, 0.8)
        ctr = round(base_ctr + noise, 2)
        curiosity = round(random.uniform(70, 95), 1)
        brand = round(random.uniform(75, 95), 1)
        click_prob = round(ctr / 10.0, 3)
        emotional = random.choice(["excitement", "curiosity", "urgency", "aspiration"])
        return CTRPrediction(
            ctr_score=ctr,
            curiosity_score=curiosity,
            brand_alignment=brand,
            click_probability=click_prob,
            emotional_hook=emotional,
        )

    async def _generate_recommendation(
        self, title: str, variants: list[ThumbnailVariant]
    ) -> str:
        best = max(variants, key=lambda v: v.ctr_prediction.ctr_score)
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                scores = ", ".join(
                    f"{v.label.value}: {v.ctr_prediction.ctr_score:.1f}%" for v in variants
                )
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Thumbnail A/B test for: '{title}'. CTR scores: {scores}. "
                            "Recommend which variant to use and briefly explain why (1 sentence)."
                        ),
                        max_tokens=100,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return (
            f"Variant {best.label.value} recommended — highest predicted CTR "
            f"({best.ctr_prediction.ctr_score:.1f}%) with "
            f"{best.ctr_prediction.emotional_hook} emotional hook."
        )

    def get_recent_assets(self, limit: int = 20) -> list[ThumbnailAsset]:
        return self._assets[-limit:]
