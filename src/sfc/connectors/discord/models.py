"""Discord connector models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DiscordEmbed(BaseModel):
    title: str = ""
    description: str = ""
    color: int = 0x1DA462  # SFC green
    fields: list[dict[str, Any]] = Field(default_factory=list)
    footer: str = ""
    thumbnail_url: str = ""
    image_url: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class DiscordMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_message_id: str = ""
    channel_id: str = ""
    content: str = ""
    embed: DiscordEmbed | None = None
    file_url: str = ""
    filename: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class DiscordConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    messages_sent: int = 0
    embeds_sent: int = 0
    files_sent: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
