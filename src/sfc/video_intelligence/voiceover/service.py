"""Voice-over synthesis service for Video Intelligence clips.

Provider chain (in priority order):
  1. ElevenLabs — highest quality Arabic TTS
     Requires: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (default: Arabic voice)
  2. OpenAI TTS — broad language support
     Requires: OPENAI_API_KEY, OPENAI_TTS_VOICE (default: "alloy")
  3. No-op — returns None; rendering proceeds without voice-over

Config:
    VOICEOVER_ENABLED          — master switch (default: false)
    VOICEOVER_LANGUAGE         — BCP-47 language tag (default: ar)
    ELEVENLABS_API_KEY         — provider 1 credentials
    ELEVENLABS_VOICE_ID        — ElevenLabs voice ID (default: pNInz6obpgDQGcFmaJgB = Arabic)
    ELEVENLABS_MODEL_ID        — model (default: eleven_multilingual_v2)
    OPENAI_API_KEY             — provider 2 credentials
    OPENAI_TTS_VOICE           — OpenAI voice name (default: alloy)
    OPENAI_TTS_MODEL           — model (default: tts-1)
    VOICEOVER_STORAGE_PATH     — output directory (default: artifacts/video/voiceover)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sfc.video_intelligence.rendering.models import AudioTrack, AudioTrackType

logger = logging.getLogger("sfc.video_intelligence.voiceover")

_ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"

# Default ElevenLabs Arabic voice (Adam — multi-lingual)
_DEFAULT_ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


def _is_enabled() -> bool:
    return os.environ.get("VOICEOVER_ENABLED", "false").lower() == "true"


def _storage_path() -> Path:
    raw = os.environ.get("VOICEOVER_STORAGE_PATH", "artifacts/video/voiceover")
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


class VoiceoverService:
    """Synthesises Arabic voice-over for a clip, writes MP3 to disk."""

    def __init__(self) -> None:
        self._elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self._elevenlabs_voice = os.environ.get(
            "ELEVENLABS_VOICE_ID", _DEFAULT_ELEVENLABS_VOICE_ID
        )
        self._elevenlabs_model = os.environ.get(
            "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"
        )
        self._openai_key = os.environ.get("OPENAI_API_KEY", "")
        self._openai_voice = os.environ.get("OPENAI_TTS_VOICE", "alloy")
        self._openai_model = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
        self._language = os.environ.get("VOICEOVER_LANGUAGE", "ar")
        self._storage = _storage_path()

    def _output_path(self, clip_id: str) -> Path:
        return self._storage / f"{clip_id}.mp3"

    async def synthesise(self, clip_id: str, text: str) -> AudioTrack | None:
        """Synthesise voice-over for ``text``; returns an AudioTrack or None on failure.

        Returns None without raising so the rendering stage can proceed without
        voice-over when synthesis is unavailable.
        """
        if not _is_enabled():
            return None
        if not text.strip():
            logger.debug("[Voiceover] Empty text for clip=%s — skipping", clip_id)
            return None

        output_path = self._output_path(clip_id)
        if output_path.exists():
            logger.debug("[Voiceover] Cache hit for clip=%s", clip_id)
            return self._track(output_path)

        audio_bytes: bytes | None = None

        if self._elevenlabs_key:
            audio_bytes = await self._elevenlabs(text)
            if audio_bytes:
                logger.info("[Voiceover] ElevenLabs OK clip=%s len=%d", clip_id, len(audio_bytes))

        if audio_bytes is None and self._openai_key:
            audio_bytes = await self._openai_tts(text)
            if audio_bytes:
                logger.info("[Voiceover] OpenAI TTS OK clip=%s len=%d", clip_id, len(audio_bytes))

        if audio_bytes is None:
            logger.warning(
                "[Voiceover] No provider available for clip=%s — proceeding without voice-over",
                clip_id,
            )
            return None

        output_path.write_bytes(audio_bytes)
        return self._track(output_path)

    def _track(self, path: Path) -> AudioTrack:
        return AudioTrack(
            track_type=AudioTrackType.VOICEOVER,
            local_path=str(path),
            volume=1.0,
            start_offset_seconds=0.0,
        )

    async def _elevenlabs(self, text: str) -> bytes | None:
        try:
            import httpx

            url = _ELEVENLABS_TTS_URL.format(voice_id=self._elevenlabs_voice)
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "xi-api-key": self._elevenlabs_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json={
                        "text": text[:2500],  # ElevenLabs per-request limit
                        "model_id": self._elevenlabs_model,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.0,
                            "use_speaker_boost": True,
                        },
                    },
                )
            if resp.status_code == 200:
                return resp.content
            logger.warning(
                "[Voiceover] ElevenLabs HTTP %d: %s", resp.status_code, resp.text[:200]
            )
            return None
        except Exception as exc:
            logger.warning("[Voiceover] ElevenLabs error: %s", exc)
            return None

    async def _openai_tts(self, text: str) -> bytes | None:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    _OPENAI_TTS_URL,
                    headers={
                        "Authorization": f"Bearer {self._openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._openai_model,
                        "input": text[:4096],
                        "voice": self._openai_voice,
                        "response_format": "mp3",
                    },
                )
            if resp.status_code == 200:
                return resp.content
            logger.warning(
                "[Voiceover] OpenAI TTS HTTP %d: %s", resp.status_code, resp.text[:200]
            )
            return None
        except Exception as exc:
            logger.warning("[Voiceover] OpenAI TTS error: %s", exc)
            return None


_singleton: VoiceoverService | None = None


def get_voiceover_service() -> VoiceoverService:
    global _singleton
    if _singleton is None:
        _singleton = VoiceoverService()
    return _singleton
