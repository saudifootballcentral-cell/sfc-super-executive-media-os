# Package 10D — Master Orchestrator

## Overview

Package 10D transforms SFC Super Executive Media OS from a collection of independent operational graphs into a single operator-controlled execution platform. The orchestrator is the conductor; the existing graphs are the musicians — none of them are rebuilt.

## Architecture

```
MasterOrchestrator           ← single operator-facing entry point
  └─ WorkflowRunner          ← stage-by-stage execution loop
       ├─ ExecutionPlan       ← ordered, dependency-validated stage list
       ├─ GraphBridge         ← loads & invokes each existing graph
       ├─ ApprovalGate        ← triple-lock before any live publish
       ├─ RunContext           ← per-run dependency container
       ├─ AuditTrail          ← immutable append-only action log
       ├─ RecoveryEngine      ← retry / skip / abort on failure
       ├─ PersistenceProvider ← save/load MasterState snapshots
       └─ OrchestrationStatus ← live registry of all active runs
```

## Workflow Types

| Type | Stages | Use case |
|---|---|---|
| `FULL_PIPELINE` | All 9 stages | Production run with live publishing |
| `DRY_RUN` | All 9 stages, publishing skipped | Safe default — no live output |
| `SOCIAL_INTELLIGENCE_ONLY` | data_ingestion → social_intelligence | Trend/sentiment scan only |
| `CREATIVE_ONLY` | data_ingestion → creative → governance → approval | Asset generation review |
| `PUBLISH_ONLY` | governance → approval → publishing → analytics | Republish pre-approved content |
| `REPORTING` | data_ingestion → reporting | Executive report generation |

## Stage Sequence (Full Pipeline)

```
1. data_ingestion          — Warm Package 10A fixture/provider cache
2. social_intelligence     — 8B+8C social and narrative intelligence scan
3. main_pipeline           — Core 14-node: super_executive → learning
4. creative_production     — 8E: images, video, thumbnails, audio, shorts, podcast
5. governance_gate         — Constitutional review (hard gate, no bypass)
6. operator_approval       — Human operator must grant before live publish
7. publishing              — 9A connectors: YouTube, X, Buffer (skipped in dry_run)
8. analytics               — Post-publish metric aggregation
9. reporting               — Autonomous executive report (Package 8)
```

## Triple-Lock Publishing Gate

Live publishing requires **all three** locks:

1. `governance_approved` — set by the governance division inside the main pipeline graph
2. `operator_approved` — set by a human operator calling `grant_operator_approval()`
3. `LIVE_PUBLISHING_ENABLED=true` — environment variable kill switch (default: `false`)

If any lock is missing, `ApprovalGate.enforce()` raises `ApprovalDeniedError` and the run is aborted cleanly.

## Dry Run Mode

Dry run is the **safe default**. When `dry_run=True`:

- All intelligence, creative, and governance stages execute normally
- The publishing stage is **skipped** (marked `SKIPPED`, no error)
- A `DryRunCompleted` event is published to the EventBus
- Full audit trail is recorded
- `MasterState` reaches `RunStatus.COMPLETED`

## Quick Start

```python
from sfc.orchestration import MasterOrchestrator

# Default: dry run, no live publishing
orch = MasterOrchestrator()
state = await orch.run_dry(
    task_type="transfer_news",
    task_payload={"headline": "Neymar joins Al Hilal"},
)
print(state.status)          # RunStatus.COMPLETED
print(state.to_summary())    # full run summary

# Social intelligence scan only
state = await orch.run_social_intelligence()

# Full live run (requires operator approval + env var)
import os
os.environ["LIVE_PUBLISHING_ENABLED"] = "true"
os.environ["OPERATOR_AUTO_APPROVE"] = "true"  # staging only

state = await orch.run(
    task_type="match_report",
    workflow_type=WorkflowType.FULL_PIPELINE,
    dry_run=False,
)
```

## Operator Approval Flow

For live runs without `OPERATOR_AUTO_APPROVE`, the run pauses at `operator_approval` and emits `OperatorApprovalRequested`. Resume after human sign-off:

```python
# Run pauses here when operator_approval stage is reached
# (raises ApprovalDeniedError internally, stored in state)

# Operator grants approval via API/webhook:
orch.grant_operator_approval(run_id, granted_by="head_of_content")

# Resume the run from checkpoint:
state = await orch.resume(run_id)
```

## EventBus Integration

Package 10D is the **first** package to actively publish to the EventBus. Every stage transition emits an event:

| Event | Trigger |
|---|---|
| `OrchestrationStarted` | Run begins |
| `StageStarted` | Each stage begins |
| `StageCompleted` | Each stage finishes |
| `StageFailed` | Stage error |
| `StageSkipped` | Dry-run publishing skip |
| `OperatorApprovalRequested` | Awaiting human |
| `OperatorApprovalGranted/Denied` | Human decision recorded |
| `SocialIntelligenceRunCompleted` | Social graph finished |
| `CreativeProductionRunCompleted` | Creative graph finished |
| `ConnectorRunCompleted` | Publishing graph finished |
| `DryRunCompleted` | Dry run finished |
| `OrchestrationCompleted` | Full live run finished |
| `OrchestrationFailed` | Unrecoverable failure |
| `OrchestrationAborted` | Approval denied / governance violation |

## Persistence

Three persistence providers are available:

| Provider | Behaviour |
|---|---|
| `InMemoryPersistence` | Default; lost on restart |
| `JSONLAuditPersistence` | Append-only JSONL; survives restarts |
| `FuturePostgresPersistence` | Stub; wire `POSTGRES_DSN` when ready |

## Constitutional Guarantees

The orchestrator enforces the SFC constitution at the infrastructure level:

- **No governance bypass** — `governance_gate` stage cannot be removed from any full-pipeline workflow
- **No publishing without approval** — `ApprovalGate.enforce()` is called before every `publishing_connectors_graph` invocation
- **All actions auditable** — `AuditTrail` records every stage start/complete/fail/skip with timestamps
- **No scheduled bypass** — `WorkflowRunner` always runs governance_gate before operator_approval before publishing
- **No credential hardcoding** — all secrets via `os.environ.get()`
