from __future__ import annotations

from sfc.events.types import BaseEvent


class PersonaRegistered(BaseEvent):
    event_type: str = "persona_registered"


class PersonaActivated(BaseEvent):
    event_type: str = "persona_activated"


class PersonaDeactivated(BaseEvent):
    event_type: str = "persona_deactivated"


class PersonaAssigned(BaseEvent):
    event_type: str = "persona_assigned"


class PersonaCollaborationStarted(BaseEvent):
    event_type: str = "persona_collaboration_started"


class PersonaCollaborationCompleted(BaseEvent):
    event_type: str = "persona_collaboration_completed"


class PersonaEvaluated(BaseEvent):
    event_type: str = "persona_evaluated"


class PersonaRetired(BaseEvent):
    event_type: str = "persona_retired"


class PersonaUpdated(BaseEvent):
    event_type: str = "persona_updated"


class PersonaRecommended(BaseEvent):
    event_type: str = "persona_recommended"
