"""Transfer Window War Room models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TransferStatus(str, Enum):
    RUMOR = "rumor"
    STRONG_RUMOR = "strong_rumor"
    ADVANCED_NEGOTIATION = "advanced_negotiation"
    VERBAL_AGREEMENT = "verbal_agreement"
    OFFICIAL_CONFIRMATION = "official_confirmation"


class TransferItem(BaseModel):
    transfer_id: str = Field(default_factory=lambda: f"TRF-{uuid4().hex[:6].upper()}")
    player: str
    from_club: str
    to_club: str
    status: TransferStatus = TransferStatus.RUMOR
    fee_estimate_m_eur: float | None = None
    sources: list[str] = []
    confidence_score: float = 50.0
    is_saudi_related: bool = False
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""


class TransferTracker(BaseModel):
    window_open: bool = True
    window_type: str = "summer"
    items: list[TransferItem] = []
    total_tracked: int = 0
    saudi_related_count: int = 0
    confirmed_count: int = 0
    rumor_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
