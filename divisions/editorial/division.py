"""Editorial Division — produces news articles, analysis, and scripts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from core.models import (
    ContentItem,
    ContentStatus,
    Division,
    EventType,
    OutputScores,
    Platform,
    SFCEvent,
    Source,
)
from divisions.base import BaseDivision


class EditorialDivision(BaseDivision):
    """Produces verified written content from Intelligence signals.

    Responsibilities:
    - Breaking news articles
    - Match analysis
    - Transfer stories
    - Video scripts
    - Narrative building
    """

    division = Division.EDITORIAL

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        handlers = {
            EventType.NEWS_DETECTED: self._draft_news_article,
            EventType.TRANSFER_CONFIRMED: self._draft_transfer_story,
            EventType.MATCH_ENDED: self._draft_match_report,
            EventType.TREND_DETECTED: self._draft_trend_piece,
        }
        handler = handlers.get(EventType(event.event_type))
        if handler:
            return await handler(event)
        return None

    async def _draft_news_article(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        content = self._create_content_item(
            title=payload.get("headline", "Breaking News"),
            body=payload.get("body", ""),
            content_type="news_article",
            sources=payload.get("sources", []),
            platforms=[Platform.WEBSITE, Platform.X, Platform.TELEGRAM],
        )
        self.memory.set(f"content:{content.content_id}", content.model_dump(mode="json"))
        self.logger.info("Drafted news article: %s", content.title)
        return {"content_id": str(content.content_id), "status": "drafted", "title": content.title}

    async def _draft_transfer_story(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        player = payload.get("player", "Unknown Player")
        to_club = payload.get("to_club", "Unknown Club")
        title = f"CONFIRMED: {player} joins {to_club}"
        content = self._create_content_item(
            title=title,
            body=payload.get("details", ""),
            content_type="transfer_story",
            sources=payload.get("sources", []),
            platforms=[Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.X, Platform.WEBSITE],
        )
        self.memory.set(f"content:{content.content_id}", content.model_dump(mode="json"))
        return {"content_id": str(content.content_id), "status": "drafted", "title": title}

    async def _draft_match_report(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        home = payload.get("home_team", "Home")
        away = payload.get("away_team", "Away")
        score = payload.get("score", "0-0")
        title = f"Match Report: {home} {score} {away}"
        content = self._create_content_item(
            title=title,
            body=payload.get("report", ""),
            content_type="match_report",
            sources=payload.get("sources", []),
            platforms=[Platform.WEBSITE, Platform.YOUTUBE, Platform.X],
        )
        self.memory.set(f"content:{content.content_id}", content.model_dump(mode="json"))
        return {"content_id": str(content.content_id), "status": "drafted", "title": title}

    async def _draft_trend_piece(self, event: SFCEvent) -> dict[str, Any]:
        payload = event.payload
        topic = payload.get("topic", "Trending Topic")
        title = f"Why Everyone Is Talking About: {topic}"
        content = self._create_content_item(
            title=title,
            body=payload.get("context", ""),
            content_type="trend_analysis",
            sources=payload.get("sources", []),
            platforms=[Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.YOUTUBE_SHORTS],
        )
        self.memory.set(f"content:{content.content_id}", content.model_dump(mode="json"))
        return {"content_id": str(content.content_id), "status": "drafted", "title": title}

    def _create_content_item(
        self,
        title: str,
        body: str,
        content_type: str,
        sources: list[dict[str, Any]],
        platforms: list[Platform],
    ) -> ContentItem:
        source_objects = [
            Source(name=s.get("name", "Unknown"), url=s.get("url"), reliability_score=s.get("reliability", 80.0))
            for s in sources
        ]
        source_count = len(source_objects)
        confidence = min(100.0, 60.0 + source_count * 15.0)

        scores = OutputScores(
            confidence_score=confidence,
            risk_score=max(0.0, 100.0 - confidence),
            source_count=source_count,
            brand_alignment_score=85.0,
        )

        return ContentItem(
            title=title,
            body=body,
            content_type=content_type,
            platforms=platforms,
            status=ContentStatus.DRAFT,
            scores=scores,
            sources=source_objects,
            division=Division.EDITORIAL,
        )

    def get_all_drafts(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("content:")
        ]
