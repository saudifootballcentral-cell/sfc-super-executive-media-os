"""Audio generation provider chain — ElevenLabs → Azure Voice → provider_unavailable."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from uuid import uuid4

from sfc.creative.providers.asset_storage import get_asset_storage
from sfc.creative.providers.cost_guard import get_cost_guard
from sfc.creative.providers.generated_asset import GeneratedAsset, GeneratedAssetStatus

logger = logging.getLogger("sfc.creative.providers.audio")


class AudioProviderBase(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def credential_env_var(self) -> str: ...

    def is_available(self) -> bool:
        return bool(os.environ.get(self.credential_env_var))

    @abstractmethod
    async def synthesize(
        self,
        script: str,
        voice_id: str = "",
        language: str = "arabic",
        asset_id: str | None = None,
    ) -> GeneratedAsset: ...


class ElevenLabsProvider(AudioProviderBase):
    provider_name = "elevenlabs"
    credential_env_var = "ELEVENLABS_API_KEY"

    _DEFAULT_VOICES = {
        "arabic": "pNInz6obpgDQGcFmaJgB",
        "english": "21m00Tcm4TlvDq8ikWAM",
    }

    async def synthesize(
        self,
        script: str,
        voice_id: str = "",
        language: str = "arabic",
        asset_id: str | None = None,
    ) -> GeneratedAsset:
        import httpx

        aid = asset_id or str(uuid4())
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        vid = (
            voice_id
            or os.environ.get(f"ELEVENLABS_{language.upper()}_VOICE_ID", "")
            or self._DEFAULT_VOICES.get(language, self._DEFAULT_VOICES["english"])
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": script,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True,
                    },
                },
            )
            resp.raise_for_status()
            audio_bytes = resp.content

        storage = get_asset_storage()
        local_path, checksum, file_size = storage.save_file(
            audio_bytes, aid, "audio", "mp3"
        )
        public_base = os.environ.get("CREATIVE_PUBLIC_BASE_URL", "")
        public_url = f"{public_base}/audio/{aid}.mp3" if public_base else None

        cost_guard = get_cost_guard()
        cost_guard.record_cost(aid, self.provider_name)

        asset = GeneratedAsset(
            asset_id=aid,
            asset_type="audio",
            provider=self.provider_name,
            status=GeneratedAssetStatus.GENERATED,
            local_path=local_path,
            public_url=public_url,
            mime_type="audio/mpeg",
            file_size=file_size,
            checksum_sha256=checksum,
            prompt=script[:500],
            cost_estimate=cost_guard.estimate_cost(self.provider_name),
            quality_score=93.0,
            metadata={"voice_id": vid, "language": language},
        )
        storage.save_manifest(aid, asset.to_dict())
        logger.info("[ElevenLabs] Generated | id=%s size=%d", aid[:8], file_size)
        return asset


class AzureVoiceProvider(AudioProviderBase):
    provider_name = "azure_voice"
    credential_env_var = "AZURE_SPEECH_KEY"

    _VOICE_NAMES = {
        "arabic": "ar-SA-HamedNeural",
        "english": "en-US-AriaNeural",
    }
    _LANG_CODES = {
        "arabic": "ar-SA",
        "english": "en-US",
    }

    def is_available(self) -> bool:
        return bool(os.environ.get("AZURE_SPEECH_KEY")) and bool(
            os.environ.get("AZURE_SPEECH_REGION")
        )

    async def synthesize(
        self,
        script: str,
        voice_id: str = "",
        language: str = "arabic",
        asset_id: str | None = None,
    ) -> GeneratedAsset:
        import httpx

        aid = asset_id or str(uuid4())
        api_key = os.environ.get("AZURE_SPEECH_KEY", "")
        region = os.environ.get("AZURE_SPEECH_REGION", "eastus")
        voice_name = voice_id or self._VOICE_NAMES.get(language, "en-US-AriaNeural")
        lang_code = self._LANG_CODES.get(language, "en-US")

        ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="{lang_code}">'
            f'<voice name="{voice_name}">{script}</voice></speak>'
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                headers={
                    "Ocp-Apim-Subscription-Key": api_key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
                },
                content=ssml.encode("utf-8"),
            )
            resp.raise_for_status()
            audio_bytes = resp.content

        storage = get_asset_storage()
        local_path, checksum, file_size = storage.save_file(
            audio_bytes, aid, "audio", "mp3"
        )
        public_base = os.environ.get("CREATIVE_PUBLIC_BASE_URL", "")
        public_url = f"{public_base}/audio/{aid}.mp3" if public_base else None

        cost_guard = get_cost_guard()
        cost_guard.record_cost(aid, self.provider_name)

        asset = GeneratedAsset(
            asset_id=aid,
            asset_type="audio",
            provider=self.provider_name,
            status=GeneratedAssetStatus.GENERATED,
            local_path=local_path,
            public_url=public_url,
            mime_type="audio/mpeg",
            file_size=file_size,
            checksum_sha256=checksum,
            prompt=script[:500],
            cost_estimate=cost_guard.estimate_cost(self.provider_name),
            quality_score=91.0,
            metadata={"voice_name": voice_name, "language": language, "region": region},
        )
        storage.save_manifest(aid, asset.to_dict())
        logger.info("[AzureVoice] Generated | id=%s size=%d", aid[:8], file_size)
        return asset


class AudioProviderChain:
    """Tries providers in priority order; returns first success or provider_unavailable."""

    def __init__(self) -> None:
        self._providers: list[AudioProviderBase] = [
            ElevenLabsProvider(),
            AzureVoiceProvider(),
        ]

    def available_providers(self) -> list[str]:
        return [p.provider_name for p in self._providers if p.is_available()]

    async def synthesize(
        self,
        script: str,
        voice_id: str = "",
        language: str = "arabic",
        asset_id: str | None = None,
        run_id: str | None = None,
    ) -> GeneratedAsset:
        aid = asset_id or str(uuid4())
        cost_guard = get_cost_guard()

        if not cost_guard.is_generation_enabled():
            return GeneratedAsset(
                asset_id=aid,
                asset_type="audio",
                provider="none",
                status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
                prompt=script[:200],
                metadata={"reason": "GENERATE_REAL_ASSETS=false"},
            )

        available = [p for p in self._providers if p.is_available()]
        if not available:
            return GeneratedAsset(
                asset_id=aid,
                asset_type="audio",
                provider="none",
                status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
                prompt=script[:200],
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
                lambda p=provider: p.synthesize(script, voice_id, language, aid),
                operation_name=provider.provider_name,
            )
            if result.success:
                return result.result
            errors.append(f"{provider.provider_name}:{result.error}")

        logger.warning("[AudioChain] All providers failed | errors=%s", errors)
        return GeneratedAsset(
            asset_id=aid,
            asset_type="audio",
            provider="none",
            status=GeneratedAssetStatus.FAILED,
            prompt=script[:200],
            metadata={"errors": errors},
        )


_chain_singleton: "AudioProviderChain | None" = None


def get_audio_provider_chain() -> AudioProviderChain:
    global _chain_singleton
    if _chain_singleton is None:
        _chain_singleton = AudioProviderChain()
    return _chain_singleton
