"""Public Reaction Simulator models — forecasts, sentiment, and risk simulations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReactionType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CONTROVERSIAL = "controversial"


class SimulationScenario(str, Enum):
    TRANSFER_ANNOUNCEMENT = "transfer_announcement"
    MATCH_WIN = "match_win"
    MATCH_LOSS = "match_loss"
    PLAYER_SCANDAL = "player_scandal"
    CLUB_STATEMENT = "club_statement"
    COACH_CHANGE = "coach_change"
    TOURNAMENT_EXIT = "tournament_exit"
    TITLE_WIN = "title_win"
    SPONSORSHIP_DEAL = "sponsorship_deal"
    REFEREE_CONTROVERSY = "referee_controversy"


class AudienceReactionForecast(BaseModel):
    audience_type: str
    positive_probability: float = 0.0       # 0-100
    neutral_probability: float = 0.0        # 0-100
    negative_probability: float = 0.0       # 0-100
    expected_engagement_multiplier: float = 1.0
    expected_sentiment_shift: float = 0.0   # -50 to +50
    controversy_probability: float = 0.0    # 0-100

    model_config = {"frozen": False}

    @property
    def dominant_reaction(self) -> ReactionType:
        probs = {
            ReactionType.POSITIVE: self.positive_probability,
            ReactionType.NEUTRAL: self.neutral_probability,
            ReactionType.NEGATIVE: self.negative_probability,
        }
        dominant = max(probs, key=lambda k: probs[k])
        if self.controversy_probability > 60:
            return ReactionType.CONTROVERSIAL
        return dominant

    def to_dict(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "dominant_reaction": self.dominant_reaction.value}


class SponsorReaction(BaseModel):
    sponsor_type: str = ""
    risk_level: str = "low"         # low | medium | high | critical
    estimated_revenue_impact: float = 0.0   # % change
    reputation_risk_score: float = 0.0      # 0-100
    likely_response: str = ""
    mitigation_needed: bool = False

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MediaReaction(BaseModel):
    coverage_probability: float = 0.0   # 0-100 likelihood of coverage
    tone_forecast: str = "neutral"       # positive | neutral | negative
    amplification_factor: float = 1.0   # expected spread multiplier
    narrative_framing: str = ""          # predicted media angle
    key_outlets: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ReactionForecast(BaseModel):
    forecast_id: str = Field(default_factory=lambda: str(uuid4()))
    scenario: SimulationScenario
    narrative_id: str = ""
    content_description: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    # Audience reactions
    audience_reactions: list[AudienceReactionForecast] = Field(default_factory=list)
    sponsor_reaction: SponsorReaction = Field(default_factory=SponsorReaction)
    media_reaction: MediaReaction = Field(default_factory=MediaReaction)
    # Aggregates
    overall_positive_probability: float = 0.0
    overall_negative_probability: float = 0.0
    overall_controversy_risk: float = 0.0
    expected_sentiment_delta: float = 0.0
    expected_reach_multiplier: float = 1.0
    # Risk
    risk_score: float = 0.0         # 0-100
    risk_narrative: str = ""
    recommended_timing: str = ""
    proceed_recommendation: bool = True
    ai_analysis: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        proceed = "PROCEED" if self.proceed_recommendation else "HOLD"
        return (
            f"Scenario: {self.scenario.value.replace('_', ' ')} — "
            f"{self.overall_positive_probability:.0f}% positive, "
            f"{self.overall_negative_probability:.0f}% negative, "
            f"risk: {self.risk_score:.0f}/100. Recommendation: {proceed}."
        )
