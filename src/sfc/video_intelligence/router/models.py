"""Production router models — decision between Mode A / B / C."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProductionMode(str, Enum):
    REAL_FOOTAGE = "real_footage"   # Mode A — use ingested source footage
    AI_VIDEO = "ai_video"           # Mode B — generate entirely with AI
    HYBRID = "hybrid"               # Mode C — mix real footage + AI-generated scenes


@dataclass
class RouterDecision:
    """Result of the production router decision."""
    mode: ProductionMode
    reason: str
    real_footage_available: bool = False
    ai_video_available: bool = False
    confidence: float = 1.0
    recommended_platforms: list[str] = field(default_factory=list)
