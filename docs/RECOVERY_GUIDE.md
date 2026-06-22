# RecoveryEngine — Retry, Skip, and Abort

## Purpose

`RecoveryEngine` applies recovery strategies when a workflow stage fails. It prevents a single transient error from aborting a long-running workflow unnecessarily, while ensuring governance and approval violations are always fatal.

## Strategies

| Strategy | When applied |
|---|---|
| `RETRY` | Transient errors; retries remaining |
| `SKIP` | Non-required stages only |
| `ABORT` | Retries exhausted; governance/approval errors |
| `ROLLBACK` | Reserved for future use |

## Configuration

```python
from sfc.orchestration.recovery import RecoveryEngine

engine = RecoveryEngine(
    max_retries=2,                # retries per stage (default: 2)
    base_backoff_seconds=1.0,     # doubles on each retry (1s, 2s, 4s...)
)
```

## Retry Logic

```python
# WorkflowRunner usage pattern:
if recovery.can_retry(stage_name):
    result = await recovery.attempt_retry(stage_name, fn)
    if result.success:
        # stage recovered
    else:
        # mark failed, check should_abort()
```

Each `attempt_retry()` call:
1. Checks retry count — returns `ABORT` result if exhausted
2. Waits `base_backoff * 2^count` seconds
3. Increments retry count
4. Calls `fn()` once
5. Returns `RecoveryResult(success=True)` or `RecoveryResult(success=False)`

## Governance Hard-Stop

`should_abort()` returns `True` immediately for errors containing "governance", "constitution", or "approval" in their message. These errors are never retried — they indicate intentional blocks, not transient failures.

## Per-Stage Isolation

Retry counts are tracked per `stage_name`. A failure in `social_intelligence` does not consume retries for `creative_production`. Call `reset_stage(name)` to clear a stage's count (e.g., after manual intervention).
