"""Webhook connector models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    payload_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WebhookResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    webhook_url: str = ""
    status_code: int = 200
    success: bool = True
    response_body: str = ""
    latency_ms: float = 0.0
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WebhookConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    webhooks_sent: int = 0
    broadcasts_sent: int = 0
    total_endpoints: int = 0
    success_count: int = 0
    failure_count: int = 0
    api_errors: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
