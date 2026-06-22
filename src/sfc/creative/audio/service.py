"""AI Audio Factory Service — Arabic and English voice content generation."""

from __future__ import annotations

import logging
import os
import random
from typing import Any

from sfc.creative.audio.models import (
    AudioAsset,
    AudioPackage,
    AudioProvider,
    AudioType,
    VoiceLanguage,
)

logger = logging.getLogger("sfc.creative.audio")

_singleton: "AudioFactoryService | None" = None


def get_audio_factory_service() -> "AudioFactoryService":
    global _singleton
    if _singleton is None:
        _singleton = AudioFactoryService()
    return _singleton


class AudioFactoryService:
    """Generates AI voice and audio content for SFC."""

    _VOICE_IDS = {
        VoiceLanguage.ARABIC: "arabic_male_sports_01",
        VoiceLanguage.ENGLISH: "english_male_sports_01",
    }

    def __init__(self) -> None:
        self._gateway = None
        self._assets: list[AudioAsset] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def generate_audio(
        self,
        title: str,
        script: str = "",
        audio_type: AudioType = AudioType.NEWS_BRIEF,
        language: VoiceLanguage = VoiceLanguage.ARABIC,
        platform: str = "spotify",
        context: dict[str, Any] | None = None,
    ) -> AudioAsset:
        """Generate a voice audio asset from script."""
        context = context or {}
        if not script:
            script = await self._generate_script(title, audio_type, language, context)
        word_count = len(script.split())
        wpm = 140 if language == VoiceLanguage.ARABIC else 160
        duration = round((word_count / wpm) * 60, 1)
        provider = self._select_provider(language)
        quality = round(random.uniform(85, 97), 1)

        # Default mock URL for planning / dry-run mode
        file_url = f"https://assets.sfc.sa/audio/mock/{audio_type.value}_{language.value}.mp3"

        use_real = os.environ.get("GENERATE_REAL_ASSETS", "false").lower() == "true"
        if use_real:
            from sfc.creative.providers.audio_providers import get_audio_provider_chain
            from sfc.creative.providers.generated_asset import GeneratedAssetStatus
            chain = get_audio_provider_chain()
            generated = await chain.synthesize(
                script=script,
                voice_id=self._VOICE_IDS.get(language, ""),
                language=language.value,
            )
            if generated.status == GeneratedAssetStatus.GENERATED:
                file_url = generated.local_path
                quality = generated.quality_score
                provider = AudioProvider(generated.provider) if generated.provider in [p.value for p in AudioProvider] else provider
            else:
                # Provider unavailable — no real file
                file_url = ""

        asset = AudioAsset(
            audio_type=audio_type,
            provider=provider,
            language=language,
            title=title,
            script=script,
            voice_id=self._VOICE_IDS.get(language, "default_voice"),
            duration_seconds=duration,
            file_url=file_url,
            platform=platform,
            quality_score=quality,
            word_count=word_count,
        )
        self._assets.append(asset)
        logger.info(
            "[AudioFactory] Generated | type=%s lang=%s duration=%.0fs",
            audio_type.value,
            language.value,
            duration,
        )
        return asset

    async def generate_package(
        self,
        title: str,
        narratives: list[str],
        language: VoiceLanguage = VoiceLanguage.ARABIC,
        platform: str = "spotify",
    ) -> AudioPackage:
        """Generate a multi-segment audio package."""
        assets: list[AudioAsset] = []
        types = [AudioType.INTRO_JINGLE, AudioType.NEWS_BRIEF, AudioType.NARRATION, AudioType.SPONSOR_READ]
        for i, narrative in enumerate(narratives[:4]):
            asset = await self.generate_audio(
                title=f"{title} — {narrative[:30]}",
                audio_type=types[i % len(types)],
                language=language,
                platform=platform,
                context={"narrative": narrative},
            )
            assets.append(asset)

        total_duration = sum(a.duration_seconds for a in assets)
        return AudioPackage(
            title=title,
            language=language,
            assets=assets,
            total_duration_seconds=total_duration,
            platform=platform,
            total_assets=len(assets),
        )

    async def _generate_script(
        self,
        title: str,
        audio_type: AudioType,
        language: VoiceLanguage,
        context: dict[str, Any],
    ) -> str:
        lang_instruction = "in Arabic" if language == VoiceLanguage.ARABIC else "in English"
        type_guidance = {
            AudioType.NARRATION: "sports documentary narration",
            AudioType.MATCH_RECAP: "exciting match recap",
            AudioType.NEWS_BRIEF: "concise news brief (30 seconds)",
            AudioType.SPONSOR_READ: "sponsor acknowledgement (15 seconds)",
            AudioType.PODCAST_SEGMENT: "podcast discussion segment (2 minutes)",
            AudioType.INTRO_JINGLE: "short show intro (10 seconds)",
        }.get(audio_type, "sports content")

        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Write a {type_guidance} script {lang_instruction} for: '{title}'. "
                            "SFC Saudi football media. Professional broadcast style. "
                            "Keep it concise and energetic."
                        ),
                        max_tokens=300,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return (
            f"[SFC AUDIO — {audio_type.value.upper()}] {title}. "
            f"Saudi Football Council brings you the latest from Saudi football. "
            f"Stay tuned to SFC for all the action."
        )

    def _select_provider(self, language: VoiceLanguage) -> AudioProvider:
        if language == VoiceLanguage.ARABIC:
            return random.choice([AudioProvider.AZURE_VOICE, AudioProvider.ELEVENLABS])
        return random.choice([AudioProvider.ELEVENLABS, AudioProvider.OPENAI_VOICE])

    def get_recent_assets(self, limit: int = 20) -> list[AudioAsset]:
        return self._assets[-limit:]
