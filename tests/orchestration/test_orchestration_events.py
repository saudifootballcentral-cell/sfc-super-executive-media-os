"""Tests for Package 10D orchestration event types."""

from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.events.types import EVENT_TYPE_MAP, BaseEvent
from sfc.orchestration.orchestration_events import (
    ConnectorRunCompleted,
    CreativeProductionRunCompleted,
    DataIngestionCompleted,
    DryRunCompleted,
    NarrativeIntelligenceRunCompleted,
    OperatorApprovalDenied,
    OperatorApprovalGranted,
    OperatorApprovalRequested,
    OrchestrationAborted,
    OrchestrationCompleted,
    OrchestrationFailed,
    OrchestrationStarted,
    RecoveryAttempted,
    SocialIntelligenceRunCompleted,
    StageCompleted,
    StageFailed,
    StageSkipped,
    StageStarted,
    WorkflowCheckpointSaved,
)

_ALL_ORCH_EVENTS = [
    OrchestrationStarted,
    OrchestrationCompleted,
    OrchestrationFailed,
    OrchestrationAborted,
    StageStarted,
    StageCompleted,
    StageFailed,
    StageSkipped,
    OperatorApprovalRequested,
    OperatorApprovalGranted,
    OperatorApprovalDenied,
    DataIngestionCompleted,
    SocialIntelligenceRunCompleted,
    NarrativeIntelligenceRunCompleted,
    CreativeProductionRunCompleted,
    ConnectorRunCompleted,
    WorkflowCheckpointSaved,
    RecoveryAttempted,
    DryRunCompleted,
]


class TestOrchestrationEventTypes:
    @pytest.mark.parametrize("event_cls", _ALL_ORCH_EVENTS)
    def test_event_is_subclass_of_base_event(self, event_cls):
        assert issubclass(event_cls, BaseEvent)

    @pytest.mark.parametrize("event_cls", _ALL_ORCH_EVENTS)
    def test_event_type_in_event_type_map(self, event_cls):
        instance = event_cls(division="orchestration", run_id="test-run")
        assert instance.event_type in EVENT_TYPE_MAP

    @pytest.mark.parametrize("event_cls", _ALL_ORCH_EVENTS)
    def test_event_map_maps_to_correct_class(self, event_cls):
        instance = event_cls(division="orchestration", run_id="test-run")
        assert EVENT_TYPE_MAP[instance.event_type] is event_cls

    def test_orchestration_started_has_event_id(self):
        e = OrchestrationStarted(division="orchestration", run_id="abc")
        assert e.event_id is not None

    def test_orchestration_events_are_frozen(self):
        e = OrchestrationStarted(division="orchestration", run_id="abc")
        with pytest.raises(Exception):
            e.run_id = "mutated"  # type: ignore[misc]

    def test_event_bus_accepts_orchestration_events(self):
        bus = get_event_bus()
        bus.reset()
        e = OrchestrationStarted(division="orchestration", run_id="bus-test")
        bus.publish(e)
        history = bus.get_history()
        assert any(h.event_type == "orchestration_started" for h in history)

    def test_total_event_types_in_map(self):
        orchestration_keys = [
            k for k in EVENT_TYPE_MAP if k.startswith(("orchestration_", "stage_", "operator_approval_",
                                                          "data_ingestion", "social_intelligence_run",
                                                          "narrative_intelligence_run", "creative_production_run",
                                                          "connector_run", "workflow_checkpoint", "recovery_",
                                                          "dry_run"))
        ]
        assert len(orchestration_keys) == 19
