"""AI Audio Factory models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AudioProvider(str, Enum):
    ELEVENLABS = "elevenlabs"
    AZURE_VOICE = "azure_voice"
    OPENAI_VOICE = "openai_voice"


class VoiceLanguage(str, Enum):
    ARABIC = "arabic"
    ENGLISH = "english"


class AudioType(str, Enum):
    NARRATION = "narration"
    MATCH_RECAP = "match_recap"
    NEWS_BRIEF = "news_brief"
    SPONSOR_READ = "sponsor_read"
    PODCAST_SEGMENT = "podcast_segment"
    INTRO_JINGLE = "intro_jingle"


class AudioAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    audio_type: AudioType
    provider: AudioProvider = AudioProvider.ELEVENLABS
    language: VoiceLanguage = VoiceLanguage.ARABIC
    title: str = ""
    script: str = ""
    voice_id: str = ""
    duration_seconds: float = 0.0
    file_url: str = ""
    platform: str = ""
    quality_score: float = 0.0
    word_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[{self.audio_type.value}] '{self.title}' — "
            f"{self.language.value}, {self.duration_seconds:.0f}s, "
            f"provider: {self.provider.value}."
        )


class AudioPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    title: str = ""
    language: VoiceLanguage = VoiceLanguage.ARABIC
    platform: str = ""
    assets: list[AudioAsset] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_assets: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"AudioPackage '{self.title}' — {self.total_assets} assets, "
            f"{self.total_duration_seconds:.0f}s total, language: {self.language.value}."
        )
