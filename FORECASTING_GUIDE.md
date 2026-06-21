# AI Cost Forecasting Guide

## Overview

`CostForecastService` reads live data from the existing `CostTracker` singleton and projects costs forward across 5 time periods. It generates budget alerts and optimization recommendations automatically.

## Quick Start

```python
from sfc.forecasting.cost.service import get_cost_forecast_service, CostForecastService
from sfc.forecasting.cost.models import ForecastPeriod

# Use the process-level singleton
service = get_cost_forecast_service()

# Or create a fresh instance
service = CostForecastService()

# Generate a single-period forecast
forecast = service.forecast(ForecastPeriod.MONTHLY)

# Generate all 5 periods at once
all_forecasts = service.forecast_all_periods()
# Returns: {"daily": {...}, "weekly": {...}, "monthly": {...}, "quarterly": {...}, "annual": {...}}
```

## Forecast Periods

| Period | Days | Typical Budget |
|--------|------|----------------|
| `DAILY` | 1 | $100 (env: MAX_DAILY_AI_COST) |
| `WEEKLY` | 7 | $700 |
| `MONTHLY` | 30 | $3,000 |
| `QUARTERLY` | 90 | $9,000 |
| `ANNUAL` | 365 | $36,500 |

## CostForecast Fields

```python
forecast.period                    # ForecastPeriod.MONTHLY
forecast.run_rate_usd_per_day      # estimated daily spend rate
forecast.forecast_total_usd        # projected spend for period
forecast.budget_limit_usd          # period budget cap
forecast.budget_utilization_pct    # % of budget consumed
forecast.within_budget             # bool
forecast.days_until_budget_exhausted  # None if not applicable
forecast.by_provider               # {"anthropic": 15.0, ...}
forecast.by_model                  # {"claude-sonnet": 12.0, ...}
forecast.provider_forecasts        # list[ProviderForecast]
forecast.budget_alerts             # list of alert strings
forecast.optimization_recommendations  # list of rec strings
forecast.total_calls_this_session  # total AI calls this run
forecast.fallback_rate_pct         # % using deterministic fallback
```

## Budget Configuration

Set via environment variable:

```bash
export MAX_DAILY_AI_COST=100.0    # default: 100
```

## Budget Alerts

Alerts are triggered at three thresholds:
- **60%** utilization: "Budget at X% — monitor closely"
- **80%** utilization: "Budget at X% — approaching limit"
- **100%+** utilization: "BUDGET EXCEEDED"

## Optimization Recommendations

The service automatically generates recommendations when:
- Utilization > 50% → suggest switching to claude-haiku
- Opus model in use → suggest reserving for executive decisions only
- High fallback rate → check API key configuration

## History

```python
history = service.get_history()  # list of dict, last 50 forecasts
```

## Export

```python
markdown = forecast.to_markdown()
data = forecast.to_dict()
```
