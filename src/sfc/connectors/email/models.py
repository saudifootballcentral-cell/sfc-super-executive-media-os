"""Email/Newsletter connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EmailCampaignStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"
    QUEUED = "queued"
    SCHEDULED = "scheduled"


class EmailCampaign(BaseModel):
    campaign_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_campaign_id: str = ""
    subject: str = ""
    html_content: str = ""
    recipient_count: int = 0
    status: EmailCampaignStatus = EmailCampaignStatus.SENT
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EmailStats(BaseModel):
    campaign_id: str = ""
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EmailConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    newsletters_sent: int = 0
    single_emails_sent: int = 0
    total_recipients: int = 0
    avg_open_rate: float = 0.0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
