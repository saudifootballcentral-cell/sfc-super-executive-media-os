"""Report delivery models — channels, records, and delivery status."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DeliveryChannel(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DASHBOARD = "dashboard"
    MARKDOWN_EXPORT = "markdown_export"
    JSON_EXPORT = "json_export"
    # Future
    SLACK = "slack"
    TEAMS = "teams"
    NOTION = "notion"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeliveryRecord(BaseModel):
    """Record of a single report delivery attempt."""

    delivery_id: str = Field(default_factory=lambda: str(uuid4()))
    report_id: str
    report_type: str
    channel: DeliveryChannel
    recipient: str = ""
    status: DeliveryStatus = DeliveryStatus.PENDING
    delivered_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}
