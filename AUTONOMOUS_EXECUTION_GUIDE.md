# Autonomous Execution Guide

## Overview

The `AutonomousExecutionManager` coordinates all trigger-fired and scheduled workflow execution. It maintains a priority queue, enforces concurrency limits, and routes every request through the main SFC pipeline graph — which enforces the governance gate.

## Architecture

```
TriggerEngine → TriggerEvent
             → ExecutionRequest → AutonomousExecutionManager._queue
                                → _worker_loop (asyncio.PriorityQueue)
                                → graph.ainvoke(state)   ← main pipeline with governance
                                → ExecutionRecord
```

**The governance gate is never bypassed.** All content publishing routes through `governance_node` in the main pipeline.

## Trigger Engine

```python
from sfc.autonomous.trigger_engine import AutonomousTriggerEngine
from sfc.scheduler.triggers import TriggerConfig, TriggerType, TriggerCondition

engine = AutonomousTriggerEngine()

# Evaluate triggers against a context dict
events = await engine.evaluate(context_dict)

# Evaluate from a pipeline state dict
events = await engine.evaluate_from_state(dict(pipeline_state))

# Add a custom trigger
trigger = TriggerConfig(
    trigger_type=TriggerType.REVENUE_OPPORTUNITY_DETECTED,
    name="high_value_sponsor",
    conditions=[
        TriggerCondition(
            condition_type="threshold",
            field_path="revenue_summary.total_opportunity_usd",
            threshold=10_000,
            comparison="gte",
        )
    ],
    job_task_type="sponsor_activation",
    cooldown_seconds=1800,
)
engine.add_trigger(trigger)
```

## Default Triggers (4)

| Trigger | Type | Condition |
|---------|------|-----------|
| `cost_exceeded` | `COST_THRESHOLD_EXCEEDED` | `session_total_usd >= 50` |
| `crisis_auto` | `CRISIS_DETECTED` | Always fires (crisis context) |
| `audience_drop` | `AUDIENCE_DROP_DETECTED` | `analytics.estimated_reach < 10,000` |
| `high_value_sponsor` | `REVENUE_OPPORTUNITY_DETECTED` | `revenue.total >= 10,000` |

## All 14 Trigger Types

`TREND_DETECTED`, `CRISIS_DETECTED`, `TRANSFER_DETECTED`, `MATCH_DAY_DETECTED`,
`WORLD_CUP_DETECTED`, `BREAKING_NEWS_DETECTED`, `REVENUE_OPPORTUNITY_DETECTED`,
`GOVERNANCE_ISSUE_DETECTED`, `COST_THRESHOLD_EXCEEDED`, `AUDIENCE_DROP_DETECTED`,
`SPONSOR_OPPORTUNITY_DETECTED`, `PERSONA_PERFORMANCE_DROP`, `SCHEDULE_FIRED`, `MANUAL`

## Execution Manager

```python
from sfc.autonomous.execution_manager import get_execution_manager, ExecutionRequest

manager = get_execution_manager()  # process-level singleton
manager.set_graph(compiled_langgraph)  # inject the main pipeline

# Start the background worker
await manager.start()

# Submit a request (queued, non-blocking)
request = ExecutionRequest(
    task_type="news",
    payload={"topic": "transfer"},
    priority="high",
    source="trigger:transfer_detected",
)
request_id = await manager.submit(request)

# Execute immediately (bypasses queue — for cycle steps)
record = await manager.execute_now(request)

# Reports
plan = manager.get_execution_plan()
report = manager.get_execution_report(limit=20)
recovery = manager.get_recovery_report()

await manager.stop()
```

## Priority Order

| Priority | Queue Position |
|----------|---------------|
| `critical` | 0 (first) |
| `high` | 1 |
| `medium` | 2 (default) |
| `low` | 3 (last) |

## Concurrency

Maximum 3 concurrent workflow executions (`_MAX_CONCURRENT = 3`). Controlled by `asyncio.Semaphore`.

## ExecutionRecord

```python
record.success           # bool
record.task_type         # "news", "executive_brief", etc.
record.pipeline_stage    # last stage completed in main pipeline
record.duration_ms       # execution time
record.errors            # list[str] from pipeline
record.run_id            # pipeline run ID
```

## Failure Recovery

```python
recovery = manager.get_recovery_report()
# Returns: {"failed_count": N, "failed_task_types": [...], "recent_failures": [...]}
```

Failed executions are logged but do not crash the system. The manager retries via resubmission (caller's responsibility).
