"""AI Image Factory Service — generates branded football imagery."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.creative.image.models import (
    ImageAsset,
    ImageDimension,
    ImageFormat,
    ImageGenerationReport,
    ImageProvider,
    ImageVariant,
)

logger = logging.getLogger("sfc.creative.image")

_singleton: "ImageFactoryService | None" = None


def get_image_factory_service() -> "ImageFactoryService":
    global _singleton
    if _singleton is None:
        _singleton = ImageFactoryService()
    return _singleton


class ImageFactoryService:
    """Generates branded imagery for SFC across all platforms."""

    _STYLE_GUIDE = (
        "Saudi football aesthetic, SFC brand colors (green/gold/white), "
        "high contrast, Arabic typography compatible, premium sports editorial"
    )

    def __init__(self) -> None:
        self._gateway = None
        self._assets: list[ImageAsset] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def generate_image(
        self,
        title: str,
        subject: str = "",
        image_format: ImageFormat = ImageFormat.SOCIAL_CARD,
        platform: str = "instagram",
        context: dict[str, Any] | None = None,
        num_variants: int = 2,
    ) -> ImageAsset:
        """Generate an image asset with multiple variants."""
        context = context or {}
        prompts = await self._build_prompts(title, subject, image_format, context)
        variants = self._generate_variants(prompts, image_format, num_variants)
        primary = variants[0].variant_id if variants else ""
        brand_score = sum(v.brand_alignment_score for v in variants) / max(len(variants), 1)

        asset = ImageAsset(
            image_format=image_format,
            title=title,
            subject=subject or title,
            platform=platform,
            variants=variants,
            primary_variant_id=primary,
            brand_alignment_score=round(brand_score, 1),
            prompt_library=prompts,
            style_guide_applied=True,
        )
        self._assets.append(asset)
        logger.info(
            "[ImageFactory] Generated | format=%s variants=%d brand=%.0f",
            image_format.value,
            len(variants),
            brand_score,
        )
        return asset

    async def generate_batch(
        self,
        subjects: list[str],
        image_format: ImageFormat = ImageFormat.PLAYER_POSTER,
        platform: str = "instagram",
    ) -> ImageGenerationReport:
        """Generate a batch of images for multiple subjects."""
        assets: list[ImageAsset] = []
        for subject in subjects[:8]:
            asset = await self.generate_image(
                title=f"{image_format.value.replace('_', ' ').title()}: {subject}",
                subject=subject,
                image_format=image_format,
                platform=platform,
            )
            assets.append(asset)

        total_variants = sum(len(a.variants) for a in assets)
        avg_brand = sum(a.brand_alignment_score for a in assets) / max(len(assets), 1)
        providers = list({v.provider.value for a in assets for v in a.variants})

        return ImageGenerationReport(
            assets=assets,
            total_generated=len(assets),
            total_variants=total_variants,
            avg_brand_alignment=round(avg_brand, 1),
            providers_used=providers,
        )

    async def _build_prompts(
        self,
        title: str,
        subject: str,
        image_format: ImageFormat,
        context: dict[str, Any],
    ) -> list[str]:
        format_guidance = {
            ImageFormat.PLAYER_POSTER: "dramatic player portrait, stadium lighting",
            ImageFormat.MATCH_POSTER: "match day atmosphere, both team colors",
            ImageFormat.LINEUP: "clean tactical formation graphic",
            ImageFormat.COVER_IMAGE: "wide cinematic header, bold typography",
            ImageFormat.SOCIAL_CARD: "eye-catching square card, headline text",
            ImageFormat.INFOGRAPHIC: "clean data visualization, SFC brand",
            ImageFormat.SPONSOR_ASSET: "premium sponsor placement, SFC logo",
        }
        guidance = format_guidance.get(image_format, "sports editorial")
        base = (
            f"{subject or title}, {guidance}, {self._STYLE_GUIDE}, "
            "ultra high quality, 4K resolution"
        )
        alt = (
            f"{title}, {guidance}, Saudi football media, "
            "photorealistic, professional sports photography"
        )
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Create a concise image generation prompt (1 sentence) for: "
                            f"{title}. Context: {guidance}. SFC Saudi football brand."
                        ),
                        max_tokens=80,
                    )
                )
                ai_prompt = result.content.strip()
                return [base, alt, ai_prompt]
            except Exception:
                pass
        return [base, alt]

    def _generate_variants(
        self,
        prompts: list[str],
        image_format: ImageFormat,
        num_variants: int,
    ) -> list[ImageVariant]:
        providers = [ImageProvider.FLUX, ImageProvider.IDEOGRAM, ImageProvider.GPT_IMAGE]
        dimensions = {
            ImageFormat.COVER_IMAGE: ImageDimension.COVER,
            ImageFormat.PLAYER_POSTER: ImageDimension.PORTRAIT,
            ImageFormat.MATCH_POSTER: ImageDimension.LANDSCAPE,
        }
        dim = dimensions.get(image_format, ImageDimension.SQUARE)
        variants: list[ImageVariant] = []
        for i in range(min(num_variants, len(prompts))):
            quality = round(random.uniform(80, 97), 1)
            brand = round(random.uniform(82, 96), 1)
            variants.append(
                ImageVariant(
                    variant_label=f"v{i + 1}",
                    provider=providers[i % len(providers)],
                    prompt_used=prompts[i],
                    negative_prompt="blurry, low quality, text errors, wrong colors",
                    file_url=f"https://assets.sfc.sa/images/mock/{image_format.value}_v{i+1}.jpg",
                    dimensions=dim,
                    style="sports_editorial_arabic",
                    quality_score=quality,
                    brand_alignment_score=brand,
                )
            )
        return variants

    def get_recent_assets(self, limit: int = 20) -> list[ImageAsset]:
        return self._assets[-limit:]
