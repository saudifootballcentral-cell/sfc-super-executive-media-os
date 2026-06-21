# Operating Cycles Guide

## Overview

The `CycleService` orchestrates five operating cycle types. Each cycle runs a defined sequence of steps sequentially. Step failures are non-fatal — the cycle continues and marks itself `PARTIAL` instead of aborting.

## Cycle Definitions

| Cycle | Steps |
|-------|-------|
| **Daily** | opportunity_scan → trend_scan → executive_brief → cost_check → memory_update |
| **Weekly** | performance_review → persona_review → growth_review → war_room_review |
| **Monthly** | strategy_review → revenue_review → sponsor_review → governance_review |
| **Quarterly** | executive_planning → expansion_planning → platform_review |
| **Annual** | annual_report → strategic_reset → roadmap_planning |

## Quick Start

```python
from sfc.cycles.service import CycleService
from sfc.reporting.executive.service import ExecutiveReportService
from sfc.reporting.operational.service import OperationalReportService
from sfc.forecasting.cost.service import CostForecastService

svc = CycleService()

# Optionally inject services for richer outputs
svc.inject_services(
    executive=ExecutiveReportService(),
    operational=OperationalReportService(),
    forecast=CostForecastService(),
)

result = await svc.run_daily()
result = await svc.run_weekly()
result = await svc.run_monthly()
result = await svc.run_quarterly()
result = await svc.run_annual()
```

## CycleResult

```python
result.cycle_type    # CycleType.DAILY
result.status        # CyclePhase.COMPLETED / PARTIAL / FAILED
result.steps         # list[CycleStep] with per-step timing and errors
result.duration_ms   # total cycle duration
result.executive_report   # generated executive report dict (if any)
result.cost_forecast      # generated cost forecast dict (if any)
result.errors        # list of non-fatal step errors
```

## Phase Status Logic

| Errors | Status |
|--------|--------|
| 0 errors | `COMPLETED` |
| 1–(N-1) errors | `PARTIAL` |
| All N steps failed | `FAILED` |

## History and Summary

```python
history = svc.get_history()                          # all cycles
history = svc.get_history(cycle_type=CycleType.DAILY, limit=10)
summary = svc.get_summary()
# Returns: {"total_cycles_run": N, "by_type": {...}, "recent": [...]}
```

## Service Injection

Services are optional. Without injection, steps return lightweight stubs. With injection, steps produce full reports:

| Step | Requires |
|------|----------|
| `executive_brief` | `ExecutiveReportService` |
| `cost_check` | `CostForecastService` |
| `trend_scan`, `growth_review` | `HistoricalAnalyticsService` |
| `performance_review`, `persona_review`, `war_room_review`, etc. | `OperationalReportService` |

## Scheduling Cycles

Use `CycleCalendar` to calculate next run times:

```python
from sfc.scheduler.calendar import CycleCalendar

daily_at_7am = CycleCalendar.next_daily(hour=7)
monday_9am   = CycleCalendar.next_weekly(weekday=0, hour=9)
first_of_month = CycleCalendar.next_monthly(day=1, hour=8)
next_quarter = CycleCalendar.next_quarterly(hour=8)
jan_1_next_year = CycleCalendar.next_annual(month=1, day=1)
```
