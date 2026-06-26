"""Pinterest API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.pinterest.models import (
    PinterestAnalytics,
    PinterestConnectorReport,
    PinterestPin,
)

logger = logging.getLogger("sfc.connectors.pinterest")

_singleton: "PinterestService | None" = None


def get_pinterest_service() -> "PinterestService":
    global _singleton
    if _singleton is None:
        _singleton = PinterestService()
    return _singleton


class PinterestService:
    """Pinterest API v5 connector. All providers mocked; inject real credentials via
    PINTEREST_ACCESS_TOKEN / PINTEREST_BOARD_ID env vars."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
        self._board_id = os.environ.get("PINTEREST_BOARD_ID", "")
        self._observability = ConnectorObservability(connector="pinterest")
        self._pin_history: list[PinterestPin] = []
        self._pin_counter = 0

    def _next_pin_id(self) -> str:
        self._pin_counter += 1
        return f"pin_{uuid4().hex[:14]}_{self._pin_counter}"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_pin(
        self,
        title: str,
        description: str,
        image_url: str,
        link: str = "",
    ) -> dict[str, Any]:
        """Create an image Pin on the Pinterest board (mocked)."""
        try:
            pin_id = self._next_pin_id()
            pin = PinterestPin(
                platform_pin_id=pin_id,
                title=title,
                description=description,
                image_url=image_url,
                link=link,
                board_id=self._board_id or "mock_board",
                pin_url=f"https://www.pinterest.com/pin/{pin_id}/",
                published_at=datetime.utcnow(),
            )
            self._pin_history.append(pin)
            self._observability.record_success(latency_ms=320.0)
            logger.info("[Pinterest] Pin created | id=%s title=%s", pin_id, title[:40])
            return pin.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_video_pin(
        self,
        title: str,
        description: str,
        video_url: str,
    ) -> dict[str, Any]:
        """Create a video Pin on the Pinterest board (mocked)."""
        try:
            pin_id = self._next_pin_id()
            pin = PinterestPin(
                platform_pin_id=pin_id,
                title=title,
                description=description,
                video_url=video_url,
                board_id=self._board_id or "mock_board",
                pin_url=f"https://www.pinterest.com/pin/{pin_id}/",
                published_at=datetime.utcnow(),
            )
            self._pin_history.append(pin)
            self._observability.record_success(latency_ms=520.0)
            logger.info("[Pinterest] Video Pin created | id=%s", pin_id)
            return pin.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_pin_analytics(self, pin_id: str) -> dict[str, Any]:
        """Get analytics for a specific Pin (mocked)."""
        try:
            analytics = PinterestAnalytics(
                pin_id=pin_id,
                impressions=8_400,
                saves=320,
                clicks=680,
                outbound_clicks=420,
                engagement_rate=5.2,
            )
            self._observability.record_success(latency_ms=135.0)
            return analytics.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_board_analytics(self) -> dict[str, Any]:
        """Get analytics for the Pinterest board (mocked)."""
        try:
            self._observability.record_success(latency_ms=150.0)
            return {
                "board_id": self._board_id or "mock_board",
                "total_pins": 284,
                "followers": 12_400,
                "impressions_30d": 184_000,
                "saves_30d": 8_400,
                "clicks_30d": 6_200,
                "outbound_clicks_30d": 3_800,
                "avg_engagement_rate": 4.8,
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> PinterestConnectorReport:
        video_pins = sum(1 for p in self._pin_history if p.video_url)
        return PinterestConnectorReport(
            pins_created=len(self._pin_history),
            video_pins_created=video_pins,
            total_impressions=len(self._pin_history) * 8_400,
            total_saves=len(self._pin_history) * 320,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._board_id)
