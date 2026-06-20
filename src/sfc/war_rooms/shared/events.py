"""War Room event types extending the base event bus."""

from __future__ import annotations

from sfc.events.types import BaseEvent


class WarRoomActivated(BaseEvent):
    event_type: str = "war_room_activated"
    # payload contains: war_room_id, war_room_type, priority


class WarRoomDeactivated(BaseEvent):
    event_type: str = "war_room_deactivated"


class WarRoomEscalated(BaseEvent):
    event_type: str = "war_room_escalated"


class ResourceAllocated(BaseEvent):
    event_type: str = "resource_allocated"


class PriorityChanged(BaseEvent):
    event_type: str = "priority_changed"


class CrisisTriggered(BaseEvent):
    event_type: str = "crisis_triggered"


class MatchTriggered(BaseEvent):
    event_type: str = "match_triggered"


class WorldCupTriggered(BaseEvent):
    event_type: str = "world_cup_triggered"


class TransferWindowTriggered(BaseEvent):
    event_type: str = "transfer_window_triggered"


class WarRoomClosed(BaseEvent):
    event_type: str = "war_room_closed"


class BreakingNewsDetected(BaseEvent):
    event_type: str = "breaking_news_detected"


class ExecutiveAlertTriggered(BaseEvent):
    event_type: str = "executive_alert_triggered"


class EscalationTriggered(BaseEvent):
    event_type: str = "escalation_triggered"


class EscalationResolved(BaseEvent):
    event_type: str = "escalation_resolved"


class IncidentDetected(BaseEvent):
    event_type: str = "incident_detected"


class IncidentResolved(BaseEvent):
    event_type: str = "incident_resolved"


class MonitoringAlertRaised(BaseEvent):
    event_type: str = "monitoring_alert_raised"


class OperationalFailureDetected(BaseEvent):
    event_type: str = "operational_failure_detected"


class CoordinationConflictDetected(BaseEvent):
    event_type: str = "coordination_conflict_detected"


class DashboardUpdated(BaseEvent):
    event_type: str = "dashboard_updated"
