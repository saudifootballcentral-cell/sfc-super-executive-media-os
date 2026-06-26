"""Pinterest API connector models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PinterestPin(BaseModel):
    pin_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_pin_id: str = ""
    title: str = ""
    description: str = ""
    image_url: str = ""
    video_url: str = ""
    link: str = ""
    board_id: str = ""
    pin_url: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PinterestAnalytics(BaseModel):
    pin_id: str = ""
    impressions: int = 0
    saves: int = 0
    clicks: int = 0
    outbound_clicks: int = 0
    engagement_rate: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PinterestConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    pins_created: int = 0
    video_pins_created: int = 0
    total_impressions: int = 0
    total_saves: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
