# ApprovalGate — Triple-Lock Publishing Control

## Purpose

The `ApprovalGate` is the constitutional enforcement point that prevents any content from reaching live platforms unless three independent locks are satisfied simultaneously.

## The Three Locks

### Lock 1: `governance_approved`
Set by the governance division inside the main pipeline LangGraph graph. The governance node performs constitutional compliance checks:
- Minimum 2 verified sources
- Confidence score ≥ 85
- Brand alignment
- Risk scoring
- Rumor labeling

This lock is set automatically by `WorkflowRunner._stage_governance_gate()` after the main pipeline executes.

### Lock 2: `operator_approved`
Set by a human operator calling `MasterOrchestrator.grant_operator_approval(run_id)`. This is a deliberate human-in-the-loop requirement — no automated system can set this to `True` except via `OPERATOR_AUTO_APPROVE=true` (which must never be set in production).

### Lock 3: `LIVE_PUBLISHING_ENABLED=true` (environment variable)
A deployment-level kill switch. Default is `false`. Setting it to `true` is an explicit infrastructure decision.

## Evaluation Logic

```python
gate = ApprovalGate()
decision = gate.evaluate(state)
# decision.approved: True only if ALL three locks are True
# decision.reason:   "all_checks_passed" | "dry_run_mode" | "blocked_by:..."
# decision.checks:   dict of each lock's current value
```

## Dry Run Behaviour

When `MasterState.dry_run=True`, `evaluate()` returns `approved=False` with `reason="dry_run_mode"`. The publishing stage is **skipped gracefully** — no `ApprovalDeniedError` is raised. This is intentional: dry runs complete normally, they just don't publish.

## Enforcement

```python
gate.enforce(state)  # raises ApprovalDeniedError if not fully approved
```

`WorkflowRunner` calls `enforce()` in `_stage_operator_approval()` only when `dry_run=False`. Any `ApprovalDeniedError` terminates the run with `RunStatus.ABORTED` — no retry.

## Granting / Denying Approval

```python
# Grant (human operator action):
gate.grant_operator_approval(state, granted_by="ceo", reason="Verified content")
# → sets state.approval.operator_approved = True
# → sets state.status = RunStatus.APPROVED
# → appends to execution_history

# Deny:
gate.deny_operator_approval(state, denied_by="compliance", reason="Unverified source")
# → sets state.status = RunStatus.ABORTED
```

## Security Constraints

- `ApprovalDeniedError` is a hard stop — the RecoveryEngine does NOT retry on governance/approval errors
- The triple-lock cannot be reduced to a double-lock in code — all three fields are checked simultaneously
- `LIVE_PUBLISHING_ENABLED` must never be hardcoded — always read via `os.environ.get()`
