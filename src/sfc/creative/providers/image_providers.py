"""Image generation provider chain — OpenAI → Flux → Ideogram → provider_unavailable."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from uuid import uuid4

from sfc.creative.providers.asset_storage import get_asset_storage
from sfc.creative.providers.cost_guard import get_cost_guard
from sfc.creative.providers.generated_asset import GeneratedAsset, GeneratedAssetStatus

logger = logging.getLogger("sfc.creative.providers.image")


class ImageProviderBase(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def credential_env_var(self) -> str: ...

    def is_available(self) -> bool:
        return bool(os.environ.get(self.credential_env_var))

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        dimensions: str = "1080x1080",
        negative_prompt: str = "",
        asset_id: str | None = None,
    ) -> GeneratedAsset: ...


class OpenAIImageProvider(ImageProviderBase):
    provider_name = "openai_image"
    credential_env_var = "OPENAI_API_KEY"

    _SIZE_MAP: dict[str, str] = {
        "1080x1080": "1024x1024",
        "1080x1350": "1024x1792",
        "1080x1920": "1024x1792",
        "1280x720": "1792x1024",
        "1584x396": "1792x1024",
    }

    async def generate(
        self,
        prompt: str,
        dimensions: str = "1080x1080",
        negative_prompt: str = "",
        asset_id: str | None = None,
    ) -> GeneratedAsset:
        import base64

        import httpx

        aid = asset_id or str(uuid4())
        api_key = os.environ.get("OPENAI_API_KEY", "")
        size = self._SIZE_MAP.get(dimensions, "1024x1024")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt[:4000],
                    "n": 1,
                    "size": size,
                    "response_format": "b64_json",
                },
            )
            resp.raise_for_status()
            image_bytes = base64.b64decode(resp.json()["data"][0]["b64_json"])

        return self._build_asset(aid, image_bytes, prompt, negative_prompt, "png")

    def _build_asset(
        self,
        aid: str,
        content: bytes,
        prompt: str,
        negative_prompt: str,
        ext: str,
    ) -> GeneratedAsset:
        storage = get_asset_storage()
        local_path, checksum, file_size = storage.save_file(content, aid, "image", ext)
        public_base = os.environ.get("CREATIVE_PUBLIC_BASE_URL", "")
        public_url = f"{public_base}/images/{aid}.{ext}" if public_base else None

        cost_guard = get_cost_guard()
        cost_guard.record_cost(aid, self.provider_name)

        asset = GeneratedAsset(
            asset_id=aid,
            asset_type="image",
            provider=self.provider_name,
            status=GeneratedAssetStatus.GENERATED,
            local_path=local_path,
            public_url=public_url,
            mime_type=f"image/{ext}",
            file_size=file_size,
            checksum_sha256=checksum,
            prompt=prompt,
            negative_prompt=negative_prompt,
            cost_estimate=cost_guard.estimate_cost(self.provider_name),
            quality_score=90.0,
        )
        storage.save_manifest(aid, asset.to_dict())
        logger.info("[OpenAIImage] Generated | id=%s size=%d", aid[:8], file_size)
        return asset


class FluxProvider(ImageProviderBase):
    provider_name = "flux"
    credential_env_var = "FLUX_API_KEY"

    async def generate(
        self,
        prompt: str,
        dimensions: str = "1080x1080",
        negative_prompt: str = "",
        asset_id: str | None = None,
    ) -> GeneratedAsset:
        import httpx

        aid = asset_id or str(uuid4())
        api_key = os.environ.get("FLUX_API_KEY", "")

        width, height = 1024, 1024
        if "x" in dimensions:
            try:
                w, h = dimensions.split("x")
                width, height = min(int(w), 1440), min(int(h), 1440)
            except (ValueError, IndexError):
                pass

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.bfl.ml/v1/flux-pro-1.1",
                headers={"x-key": api_key, "Content-Type": "application/json"},
                json={
                    "prompt": prompt[:2000],
                    "width": width,
                    "height": height,
                    "steps": 28,
                    "guidance": 3.5,
                },
            )
            resp.raise_for_status()
            image_url = resp.json().get("sample", "")
            img_resp = await client.get(image_url, timeout=60.0)
            img_resp.raise_for_status()
            image_bytes = img_resp.content

        storage = get_asset_storage()
        local_path, checksum, file_size = storage.save_file(
            image_bytes, aid, "image", "jpg"
        )
        public_base = os.environ.get("CREATIVE_PUBLIC_BASE_URL", "")
        public_url = f"{public_base}/images/{aid}.jpg" if public_base else None

        cost_guard = get_cost_guard()
        cost_guard.record_cost(aid, self.provider_name)

        asset = GeneratedAsset(
            asset_id=aid,
            asset_type="image",
            provider=self.provider_name,
            status=GeneratedAssetStatus.GENERATED,
            local_path=local_path,
            public_url=public_url,
            mime_type="image/jpeg",
            file_size=file_size,
            checksum_sha256=checksum,
            prompt=prompt,
            negative_prompt=negative_prompt,
            cost_estimate=cost_guard.estimate_cost(self.provider_name),
            quality_score=92.0,
        )
        storage.save_manifest(aid, asset.to_dict())
        logger.info("[Flux] Generated | id=%s size=%d", aid[:8], file_size)
        return asset


class IdeogramProvider(ImageProviderBase):
    provider_name = "ideogram"
    credential_env_var = "IDEOGRAM_API_KEY"

    async def generate(
        self,
        prompt: str,
        dimensions: str = "1080x1080",
        negative_prompt: str = "",
        asset_id: str | None = None,
    ) -> GeneratedAsset:
        import httpx

        aid = asset_id or str(uuid4())
        api_key = os.environ.get("IDEOGRAM_API_KEY", "")

        body: dict = {
            "image_request": {
                "prompt": prompt[:2048],
                "model": "V_2",
                "aspect_ratio": "ASPECT_1_1",
                "resolution": "RESOLUTION_1024_1024",
            }
        }
        if negative_prompt:
            body["image_request"]["negative_prompt"] = negative_prompt[:500]

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.ideogram.ai/generate",
                headers={"Api-Key": api_key, "Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
            image_url = resp.json()["data"][0]["url"]
            img_resp = await client.get(image_url, timeout=60.0)
            img_resp.raise_for_status()
            image_bytes = img_resp.content

        storage = get_asset_storage()
        local_path, checksum, file_size = storage.save_file(
            image_bytes, aid, "image", "png"
        )
        public_base = os.environ.get("CREATIVE_PUBLIC_BASE_URL", "")
        public_url = f"{public_base}/images/{aid}.png" if public_base else None

        cost_guard = get_cost_guard()
        cost_guard.record_cost(aid, self.provider_name)

        asset = GeneratedAsset(
            asset_id=aid,
            asset_type="image",
            provider=self.provider_name,
            status=GeneratedAssetStatus.GENERATED,
            local_path=local_path,
            public_url=public_url,
            mime_type="image/png",
            file_size=file_size,
            checksum_sha256=checksum,
            prompt=prompt,
            negative_prompt=negative_prompt,
            cost_estimate=cost_guard.estimate_cost(self.provider_name),
            quality_score=88.0,
        )
        storage.save_manifest(aid, asset.to_dict())
        logger.info("[Ideogram] Generated | id=%s size=%d", aid[:8], file_size)
        return asset


class ImageProviderChain:
    """Tries providers in priority order; returns first success or provider_unavailable."""

    def __init__(self) -> None:
        self._providers: list[ImageProviderBase] = [
            OpenAIImageProvider(),
            FluxProvider(),
            IdeogramProvider(),
        ]

    def available_providers(self) -> list[str]:
        return [p.provider_name for p in self._providers if p.is_available()]

    async def generate(
        self,
        prompt: str,
        dimensions: str = "1080x1080",
        negative_prompt: str = "",
        asset_id: str | None = None,
        run_id: str | None = None,
    ) -> GeneratedAsset:
        aid = asset_id or str(uuid4())
        cost_guard = get_cost_guard()

        if not cost_guard.is_generation_enabled():
            return GeneratedAsset(
                asset_id=aid,
                asset_type="image",
                provider="none",
                status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
                prompt=prompt,
                metadata={"reason": "GENERATE_REAL_ASSETS=false"},
            )

        available = [p for p in self._providers if p.is_available()]
        if not available:
            return GeneratedAsset(
                asset_id=aid,
                asset_type="image",
                provider="none",
                status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
                prompt=prompt,
                metadata={"reason": "no_credentials_configured"},
            )

        from sfc.creative.providers.retry import RetryExecutor

        executor = RetryExecutor(max_retries=2, base_delay=0.5, timeout_seconds=120.0)
        errors: list[str] = []

        for provider in available:
            if not cost_guard.can_afford(provider.provider_name, run_id=run_id):
                errors.append(f"{provider.provider_name}:budget_exceeded")
                continue

            result = await executor.execute(
                lambda p=provider: p.generate(prompt, dimensions, negative_prompt, aid),
                operation_name=provider.provider_name,
            )
            if result.success:
                return result.result
            errors.append(f"{provider.provider_name}:{result.error}")

        logger.warning("[ImageChain] All providers failed | errors=%s", errors)
        return GeneratedAsset(
            asset_id=aid,
            asset_type="image",
            provider="none",
            status=GeneratedAssetStatus.FAILED,
            prompt=prompt,
            metadata={"errors": errors},
        )


_chain_singleton: "ImageProviderChain | None" = None


def get_image_provider_chain() -> ImageProviderChain:
    global _chain_singleton
    if _chain_singleton is None:
        _chain_singleton = ImageProviderChain()
    return _chain_singleton
