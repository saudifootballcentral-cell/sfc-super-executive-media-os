# Scheduler Guide

## Overview

`SFCScheduler` is an asyncio-native background job scheduler. It runs a tick loop every 30 seconds and dispatches due jobs through a concurrency-limited semaphore (10 concurrent max).

## Job Types

| Type | Description | Required Field |
|------|-------------|----------------|
| `CRON` | Runs on a cron schedule | `cron_expression` |
| `INTERVAL` | Runs every N seconds | `interval_seconds` |
| `ONE_TIME` | Runs once at a specific time | `run_at` |
| `EVENT_BASED` | Triggered by system events | `event_trigger` |
| `WAR_ROOM` | Tied to war room activations | `war_room_type` |
| `PERSONA` | Tied to persona activation | `persona_id` |
| `AI_COST` | Fires when cost threshold exceeded | `cost_threshold_usd` |

## Quick Start

```python
from sfc.scheduler.engine import get_scheduler
from sfc.scheduler.jobs import make_daily_brief_job, make_trend_scan_job

scheduler = get_scheduler()
scheduler.add_job(make_daily_brief_job())       # daily 7:00 AM cron
scheduler.add_job(make_trend_scan_job(30))      # every 30 minutes

async def my_handler(job):
    # process the job
    return {"done": True}

scheduler.register_handler("executive_brief", my_handler)
await scheduler.start()
```

## Cron Expression Syntax

5-field cron: `M H dom mon dow`

| Field | Range | Example |
|-------|-------|---------|
| M (minute) | 0–59 | `0`, `*/15`, `0,30` |
| H (hour) | 0–23 | `7`, `8-18`, `*/4` |
| dom (day of month) | 1–31 | `1`, `15`, `*` |
| mon (month) | 1–12 | `*`, `1,7` |
| dow (day of week) | 0–6 | `1` = Monday, `0` = Sunday |

Examples:
- `"0 7 * * *"` — Daily at 07:00
- `"0 9 * * 1"` — Every Monday at 09:00
- `"0 0 1 * *"` — First of each month at midnight
- `"*/30 * * * *"` — Every 30 minutes
- `"0 8,18 * * *"` — At 08:00 and 18:00 daily

## Job Management

```python
job_id = scheduler.add_job(job)
scheduler.pause_job(job_id)
scheduler.resume_job(job_id)
scheduler.remove_job(job_id)
jobs = scheduler.list_jobs()
health = scheduler.get_health()
report = scheduler.get_execution_report()
```

## Trigger Management

```python
from sfc.scheduler.triggers import make_cost_exceeded_trigger, make_crisis_trigger

scheduler.add_trigger(make_cost_exceeded_trigger(threshold_usd=50.0))
scheduler.add_trigger(make_crisis_trigger())

# Evaluate all triggers against current context
fired_job_ids = await scheduler.evaluate_triggers(context_dict)
```

## Missed Job Recovery

```python
missed = scheduler.recover_missed_jobs()
# Returns list of job IDs marked as MISSED and rescheduled
```

## Pre-Built Factory Helpers

```python
from sfc.scheduler.jobs import (
    make_daily_brief_job,     # CRON: 0 7 * * *
    make_trend_scan_job,      # INTERVAL: every 30 min
    make_weekly_report_job,   # CRON: 0 9 * * 1
    make_cost_guard_job,      # AI_COST: fires at $50 threshold
)
```

## Cycle Calendar

```python
from sfc.scheduler.calendar import CycleCalendar

next_daily = CycleCalendar.next_daily(hour=7)
next_weekly = CycleCalendar.next_weekly(weekday=0)  # Monday
next_monthly = CycleCalendar.next_monthly(day=1)
next_quarterly = CycleCalendar.next_quarterly()
next_annual = CycleCalendar.next_annual()
secs = CycleCalendar.seconds_until(target_datetime)
```

## Persistence

By default, jobs are stored in memory only. Provide a `snapshot_path` for JSON file persistence:

```python
from sfc.scheduler.persistence import SchedulerPersistence
p = SchedulerPersistence(snapshot_path="/data/scheduler.json")
scheduler = SFCScheduler(persistence=p)
```
