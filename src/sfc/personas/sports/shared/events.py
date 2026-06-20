"""Sports Intelligence Persona events."""
from __future__ import annotations

from sfc.events.types import BaseEvent


class PersonaInsightGenerated(BaseEvent):
    event_type: str = "persona_insight_generated"


class OpponentAnalyzed(BaseEvent):
    event_type: str = "opponent_analyzed"


class TransferAnalyzed(BaseEvent):
    event_type: str = "transfer_analyzed"


class NarrativeDetected(BaseEvent):
    event_type: str = "narrative_detected"


class SentimentUpdated(BaseEvent):
    event_type: str = "sentiment_updated"


class TacticalAnalysisCompleted(BaseEvent):
    event_type: str = "tactical_analysis_completed"


class RefereeAnalysisCompleted(BaseEvent):
    event_type: str = "referee_analysis_completed"


class PerformanceReportGenerated(BaseEvent):
    event_type: str = "performance_report_generated"
