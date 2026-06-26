"""Telegram connector models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TelegramMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_message_id: int = 0
    chat_id: str = ""
    text: str = ""
    parse_mode: str = "HTML"
    published_at: datetime = Field(default_factory=datetime.utcnow)
    url: str = ""
    error_message: str = ""
    success: bool = True

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TelegramMedia(BaseModel):
    media_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_message_id: int = 0
    chat_id: str = ""
    text: str = ""
    media_url: str = ""
    media_type: str = "photo"
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TelegramStats(BaseModel):
    message_id: int = 0
    views: int = 0
    forwards: int = 0
    replies: int = 0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TelegramConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    messages_sent: int = 0
    media_sent: int = 0
    total_views: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
