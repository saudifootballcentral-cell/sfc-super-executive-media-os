"""Telegram Bot API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.telegram.models import (
    TelegramConnectorReport,
    TelegramMedia,
    TelegramMessage,
    TelegramStats,
)

logger = logging.getLogger("sfc.connectors.telegram")

_singleton: "TelegramService | None" = None

_MSG_ID_COUNTER = 1_000_000


def get_telegram_service() -> "TelegramService":
    global _singleton
    if _singleton is None:
        _singleton = TelegramService()
    return _singleton


class TelegramService:
    """Telegram Bot API connector. All providers mocked; inject real credentials via
    TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID env vars."""

    def __init__(self) -> None:
        self._bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._channel_id = os.environ.get("TELEGRAM_CHANNEL_ID", "")
        self._observability = ConnectorObservability(connector="telegram")
        self._message_history: list[TelegramMessage] = []
        self._media_history: list[TelegramMedia] = []
        self._msg_counter = 0

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def send_message(self, text: str, parse_mode: str = "HTML") -> dict[str, Any]:
        """Send a text message to the Telegram channel (mocked)."""
        try:
            self._msg_counter += 1
            msg_id = _MSG_ID_COUNTER + self._msg_counter
            message = TelegramMessage(
                platform_message_id=msg_id,
                chat_id=self._channel_id or "@sfc_mock_channel",
                text=text,
                parse_mode=parse_mode,
                published_at=datetime.utcnow(),
                url=f"https://t.me/sfc_mock_channel/{msg_id}",
            )
            self._message_history.append(message)
            self._observability.record_success(latency_ms=180.0)
            logger.info(
                "[Telegram] Message sent | id=%d chars=%d", msg_id, len(text)
            )
            return message.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_photo(self, text: str, photo_url: str) -> dict[str, Any]:
        """Send a photo with caption to the Telegram channel (mocked)."""
        try:
            self._msg_counter += 1
            msg_id = _MSG_ID_COUNTER + self._msg_counter
            media = TelegramMedia(
                platform_message_id=msg_id,
                chat_id=self._channel_id or "@sfc_mock_channel",
                text=text,
                media_url=photo_url,
                media_type="photo",
                published_at=datetime.utcnow(),
            )
            self._media_history.append(media)
            self._observability.record_success(latency_ms=340.0)
            logger.info("[Telegram] Photo sent | id=%d", msg_id)
            return media.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_video(self, text: str, video_url: str) -> dict[str, Any]:
        """Send a video with caption to the Telegram channel (mocked)."""
        try:
            self._msg_counter += 1
            msg_id = _MSG_ID_COUNTER + self._msg_counter
            media = TelegramMedia(
                platform_message_id=msg_id,
                chat_id=self._channel_id or "@sfc_mock_channel",
                text=text,
                media_url=video_url,
                media_type="video",
                published_at=datetime.utcnow(),
            )
            self._media_history.append(media)
            self._observability.record_success(latency_ms=580.0)
            logger.info("[Telegram] Video sent | id=%d", msg_id)
            return media.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Channel Info & Stats
    # ------------------------------------------------------------------

    async def get_channel_info(self) -> dict[str, Any]:
        """Get basic channel info (mocked)."""
        try:
            self._observability.record_success(latency_ms=120.0)
            return {
                "id": self._channel_id or "@sfc_mock_channel",
                "title": "SFC Saudi Football Media",
                "username": "sfc_football",
                "type": "channel",
                "member_count": 48_500,
                "description": "Official SFC Saudi Football media channel",
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_message_stats(self, message_id: int) -> dict[str, Any]:
        """Get views/forwards for a message (mocked)."""
        try:
            stats = TelegramStats(
                message_id=message_id,
                views=12_400 + message_id % 5000,
                forwards=380 + message_id % 200,
                replies=56 + message_id % 30,
            )
            self._observability.record_success(latency_ms=130.0)
            return stats.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> TelegramConnectorReport:
        return TelegramConnectorReport(
            messages_sent=len(self._message_history),
            media_sent=len(self._media_history),
            total_views=sum(12_400 for _ in self._message_history),
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._bot_token and self._channel_id)
