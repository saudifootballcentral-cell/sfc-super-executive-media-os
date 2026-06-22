# MasterState — Orchestration Run Envelope

## Purpose

`MasterState` is the top-level state model for a single orchestrated workflow run. It wraps the per-graph `SFCState` dicts and adds orchestration-level tracking: lifecycle status, stage records, approvals, audit history, and collected artifacts.

## Key Fields

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | UUID auto-generated per run |
| `workflow_type` | `WorkflowType` | Which stage sequence to execute |
| `status` | `RunStatus` | Current lifecycle phase |
| `dry_run` | `bool` | `True` = skip live publishing (default) |
| `stages` | `dict[str, StageRecord]` | Per-stage execution records |
| `approval` | `ApprovalRecord` | Governance + operator approval state |
| `graph_states` | `dict[str, dict]` | SFCState output from each graph run |
| `execution_history` | `list[dict]` | Append-only ordered event log |
| `decisions` | `list[dict]` | Editorial / governance decisions |
| `errors` | `list[str]` | Accumulated errors (all stages) |
| `warnings` | `list[str]` | Accumulated warnings (all stages) |
| `artifacts` | `dict[str, Any]` | Collected output artifacts |

## RunStatus Lifecycle

```
PENDING → RUNNING → AWAITING_APPROVAL → APPROVED → PUBLISHING → COMPLETED
                                                               ↓
                                                           FAILED / ABORTED
```

## StageRecord

Each stage execution is tracked in `state.stages[stage_name]`:

```python
rec = state.stages["social_intelligence"]
rec.status          # StageStatus.COMPLETED
rec.duration_ms     # 1420.5
rec.error           # "" (empty on success)
rec.artifacts       # {k: v, ...}
```

## Convenience Methods

```python
state.mark_stage_started("data_ingestion")
state.mark_stage_completed("data_ingestion", artifacts={"items": 42})
state.mark_stage_failed("publishing", "connection timeout")
state.mark_stage_skipped("publishing", reason="dry_run_mode")

state.add_decision("governance_gate", "approved", {"count": 3})
state.append_history("orchestration_started")

state.completed_stages    # ["data_ingestion", "social_intelligence", ...]
state.failed_stages       # []
state.total_duration_ms   # 8432.1
state.to_summary()        # compact dict for API responses
```

## ApprovalRecord

```python
state.approval.governance_approved   # bool — set by governance_gate stage
state.approval.operator_approved     # bool — set by human via grant_operator_approval()
state.approval.is_fully_approved     # True only when both are True
state.approval.granted_by            # "ceo"
state.approval.reason                # "Verified content"
```
