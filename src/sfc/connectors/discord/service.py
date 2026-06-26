"""Discord Bot API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.discord.models import (
    DiscordConnectorReport,
    DiscordEmbed,
    DiscordMessage,
)

logger = logging.getLogger("sfc.connectors.discord")

_singleton: "DiscordService | None" = None

_MSG_ID_BASE = 1_000_000_000_000_000_000


def get_discord_service() -> "DiscordService":
    global _singleton
    if _singleton is None:
        _singleton = DiscordService()
    return _singleton


class DiscordService:
    """Discord Bot API connector. All providers mocked; inject real credentials via
    DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID / DISCORD_SERVER_ID env vars."""

    def __init__(self) -> None:
        self._bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")
        self._channel_id = os.environ.get("DISCORD_CHANNEL_ID", "")
        self._server_id = os.environ.get("DISCORD_SERVER_ID", "")
        self._observability = ConnectorObservability(connector="discord")
        self._message_history: list[DiscordMessage] = []
        self._msg_counter = 0

    def _next_msg_id(self) -> str:
        self._msg_counter += 1
        return str(_MSG_ID_BASE + self._msg_counter)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def send_message(
        self, content: str, embed: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a message (with optional embed) to the Discord channel (mocked)."""
        try:
            msg_id = self._next_msg_id()
            embed_obj: DiscordEmbed | None = None
            if embed:
                embed_obj = DiscordEmbed(
                    title=embed.get("title", ""),
                    description=embed.get("description", ""),
                    color=embed.get("color", 0x1DA462),
                    fields=embed.get("fields", []),
                )
            message = DiscordMessage(
                platform_message_id=msg_id,
                channel_id=self._channel_id or "mock_discord_channel",
                content=content,
                embed=embed_obj,
                published_at=datetime.utcnow(),
            )
            self._message_history.append(message)
            self._observability.record_success(latency_ms=140.0)
            logger.info("[Discord] Message sent | id=%s", msg_id)
            return message.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x1DA462,
        fields: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a rich embed message to the Discord channel (mocked)."""
        try:
            msg_id = self._next_msg_id()
            embed = DiscordEmbed(
                title=title,
                description=description,
                color=color,
                fields=fields or [],
            )
            message = DiscordMessage(
                platform_message_id=msg_id,
                channel_id=self._channel_id or "mock_discord_channel",
                content="",
                embed=embed,
                published_at=datetime.utcnow(),
            )
            self._message_history.append(message)
            self._observability.record_success(latency_ms=155.0)
            logger.info("[Discord] Embed sent | id=%s title=%s", msg_id, title[:40])
            return message.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_file(
        self, content: str, file_url: str, filename: str
    ) -> dict[str, Any]:
        """Send a file attachment to the Discord channel (mocked)."""
        try:
            msg_id = self._next_msg_id()
            message = DiscordMessage(
                platform_message_id=msg_id,
                channel_id=self._channel_id or "mock_discord_channel",
                content=content,
                file_url=file_url,
                filename=filename,
                published_at=datetime.utcnow(),
            )
            self._message_history.append(message)
            self._observability.record_success(latency_ms=380.0)
            logger.info("[Discord] File sent | id=%s filename=%s", msg_id, filename)
            return message.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    async def get_channel_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve recent messages from the channel (mocked)."""
        try:
            mock_messages = [
                {
                    "id": str(_MSG_ID_BASE - i),
                    "content": f"Mock message #{i + 1} in SFC channel",
                    "author": f"SFC Bot {i % 3 + 1}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for i in range(min(limit, 5))
            ]
            self._observability.record_success(latency_ms=120.0)
            return mock_messages
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> DiscordConnectorReport:
        embeds_sent = sum(1 for m in self._message_history if m.embed is not None)
        files_sent = sum(1 for m in self._message_history if m.file_url)
        return DiscordConnectorReport(
            messages_sent=len(self._message_history),
            embeds_sent=embeds_sent,
            files_sent=files_sent,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._bot_token and self._channel_id)
