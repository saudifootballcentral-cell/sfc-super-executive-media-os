# Orchestration Events — EventBus Integration

## Overview

Package 10D is the first package to actively publish events to the `EventBus`. Every stage transition and approval decision is broadcast, enabling real-time monitoring, dashboards, and future webhook integrations.

## Event Catalogue (19 new events)

### Lifecycle

| Event type | Class | Trigger |
|---|---|---|
| `orchestration_started` | `OrchestrationStarted` | `WorkflowRunner.run()` begins |
| `orchestration_completed` | `OrchestrationCompleted` | All stages finished, live run |
| `orchestration_failed` | `OrchestrationFailed` | Unrecoverable failure |
| `orchestration_aborted` | `OrchestrationAborted` | Approval denied or governance violation |
| `dry_run_completed` | `DryRunCompleted` | All stages finished, dry run |

### Stage Transitions

| Event type | Class | Trigger |
|---|---|---|
| `stage_started` | `StageStarted` | Each stage begins |
| `stage_completed` | `StageCompleted` | Stage finishes successfully |
| `stage_failed` | `StageFailed` | Stage raises an exception |
| `stage_skipped` | `StageSkipped` | Publishing skipped in dry run |

### Approval

| Event type | Class | Trigger |
|---|---|---|
| `operator_approval_requested` | `OperatorApprovalRequested` | Run pauses for human |
| `operator_approval_granted` | `OperatorApprovalGranted` | Human grants approval |
| `operator_approval_denied` | `OperatorApprovalDenied` | Human denies, run aborted |

### Graph Completions

| Event type | Class | Trigger |
|---|---|---|
| `data_ingestion_completed` | `DataIngestionCompleted` | Package 10A cache warmed |
| `social_intelligence_run_completed` | `SocialIntelligenceRunCompleted` | 8B+8C graph finished |
| `narrative_intelligence_run_completed` | `NarrativeIntelligenceRunCompleted` | Narrative graph finished |
| `creative_production_run_completed` | `CreativeProductionRunCompleted` | 8E graph finished |
| `connector_run_completed` | `ConnectorRunCompleted` | 9A connectors finished |
| `workflow_checkpoint_saved` | `WorkflowCheckpointSaved` | Persistence snapshot written |
| `recovery_attempted` | `RecoveryAttempted` | Stage retry in progress |

## Subscribing

```python
from sfc.events.bus import get_event_bus

bus = get_event_bus()

def on_orchestration_complete(event):
    print(f"Run {event.run_id} completed: {event.payload}")

bus.subscribe("orchestration_completed", on_orchestration_complete)
bus.subscribe("stage_failed", lambda e: alert_team(e.payload))
bus.subscribe("operator_approval_requested", lambda e: notify_operator(e.run_id))
```

## All Events Are in EVENT_TYPE_MAP

All 19 new events are registered in `EVENT_TYPE_MAP` in `sfc/events/types.py`, enabling deserialization from stored payloads.
