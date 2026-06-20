"""Intelligence Division — detects trends, news, rumors, and opportunities."""

from __future__ import annotations

from typing import Any

from core.models import Division, EventType, SFCEvent
from divisions.base import BaseDivision


class IntelligenceDivision(BaseDivision):
    """Monitors Saudi football landscape for events worth acting on.

    Responsibilities:
    - Trend detection
    - News monitoring
    - Rumor tracking
    - Opportunity identification
    """

    division = Division.INTELLIGENCE

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        self.logger.info("Processing event: %s", event.event_type)

        handlers = {
            EventType.TREND_DETECTED: self._handle_trend,
            EventType.NEWS_DETECTED: self._handle_news,
            EventType.RUMOR_DETECTED: self._handle_rumor,
            EventType.TRANSFER_RUMOR: self._handle_transfer_rumor,
        }

        handler = handlers.get(EventType(event.event_type))
        if handler:
            return await handler(event)
        return None

    async def _handle_trend(self, event: SFCEvent) -> dict[str, Any]:
        trend = event.payload
        self.memory.set(f"trend:{trend.get('id', event.event_id)}", trend)
        self.logger.info("Trend captured: %s", trend.get("topic", "unknown"))
        return {
            "status": "trend_captured",
            "topic": trend.get("topic"),
            "recommended_action": "editorial_brief",
        }

    async def _handle_news(self, event: SFCEvent) -> dict[str, Any]:
        news = event.payload
        self.memory.set(f"news:{event.event_id}", news)
        priority = self._assess_priority(news)
        return {
            "status": "news_captured",
            "priority": priority,
            "headline": news.get("headline"),
        }

    async def _handle_rumor(self, event: SFCEvent) -> dict[str, Any]:
        rumor = event.payload
        self.memory.set(f"rumor:{event.event_id}", {**rumor, "_labeled": "RUMOR"})
        self.logger.warning("Rumor detected — must be labeled: %s", rumor.get("claim"))
        return {
            "status": "rumor_logged",
            "label_required": True,
            "claim": rumor.get("claim"),
        }

    async def _handle_transfer_rumor(self, event: SFCEvent) -> dict[str, Any]:
        transfer = event.payload
        self.memory.set(f"transfer_rumor:{event.event_id}", {**transfer, "_verified": False})
        return {
            "status": "transfer_rumor_logged",
            "player": transfer.get("player"),
            "clubs_involved": transfer.get("clubs", []),
            "requires_verification": True,
        }

    def _assess_priority(self, news: dict[str, Any]) -> str:
        importance = news.get("importance_score", 50)
        if importance >= 80:
            return "high"
        if importance >= 50:
            return "medium"
        return "low"

    def get_active_trends(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("trend:")
        ]

    def get_unverified_rumors(self) -> list[dict[str, Any]]:
        return [
            self.memory.get(k)
            for k in self.memory.keys()
            if k.startswith("rumor:")
        ]
