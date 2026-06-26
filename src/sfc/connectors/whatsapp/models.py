"""WhatsApp Business API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class WhatsAppMessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class WhatsAppMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_message_id: str = ""
    to: str = ""
    text: str = ""
    status: WhatsAppMessageStatus = WhatsAppMessageStatus.SENT
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str = ""
    success: bool = True

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WhatsAppMedia(BaseModel):
    media_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_message_id: str = ""
    to: str = ""
    media_url: str = ""
    media_type: str = "image"
    caption: str = ""
    status: WhatsAppMessageStatus = WhatsAppMessageStatus.SENT
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WhatsAppTemplate(BaseModel):
    template_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_message_id: str = ""
    to: str = ""
    template_name: str = ""
    params: list[str] = Field(default_factory=list)
    status: WhatsAppMessageStatus = WhatsAppMessageStatus.SENT
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WhatsAppConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    messages_sent: int = 0
    media_sent: int = 0
    templates_sent: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
