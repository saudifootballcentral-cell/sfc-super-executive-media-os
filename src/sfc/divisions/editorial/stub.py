"""Editorial Division stub — Package 2 will implement AI-powered content writing."""

from __future__ import annotations

from typing import Any

from sfc.core.models import Division
from sfc.divisions.base import DivisionInterface
from sfc.graph.state import SFCState


class EditorialDivision(DivisionInterface):
    """Editorial Division.

    Package 2 implementation will include:
    - Claude-powered breaking news articles (Arabic + English)
    - Match analysis and tactical breakdowns
    - Transfer stories with verified player/fee details
    - Short-form video scripts (TikTok/Reels/Shorts format)
    - Long-form YouTube video scripts
    - Thread/carousel writing for X and Instagram
    - Newsletter editions
    - SEO-optimised web articles
    - Tone calibration per platform persona
    """

    division = Division.EDITORIAL

    async def process(self, state: SFCState) -> dict[str, Any]:
        raise NotImplementedError("Editorial Division not yet implemented — Package 2")

    def health_check(self) -> dict[str, Any]:
        return {"division": self.division, "status": "stub", "package": 2}

    def describe(self) -> str:
        return "News, analysis, stories, scripts, and all written content"

    async def write_article(self, brief: dict[str, Any], language: str = "ar") -> dict[str, Any]:
        raise NotImplementedError

    async def write_script(self, brief: dict[str, Any], duration_seconds: int = 60) -> dict[str, Any]:
        raise NotImplementedError

    async def write_social_post(self, brief: dict[str, Any], platform: str = "x") -> dict[str, Any]:
        raise NotImplementedError

    async def write_thread(self, brief: dict[str, Any], max_posts: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError
