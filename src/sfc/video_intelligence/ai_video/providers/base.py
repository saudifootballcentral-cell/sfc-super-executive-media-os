"""Abstract base class for AI video generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sfc.video_intelligence.ai_video.models import AIVideoResult
    from sfc.video_intelligence.storyboard.models import StoryboardScene


class AIVideoProvider(ABC):
    """Base class for AI text-to-video providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (kling, runway, luma, pika)."""

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """True when the required env vars are set."""

    @abstractmethod
    async def generate(self, scene: "StoryboardScene") -> "AIVideoResult":
        """Generate video for a single storyboard scene."""
