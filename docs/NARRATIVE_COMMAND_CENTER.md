# Narrative Command Center

## Overview

The Narrative Command Center is the top-level orchestrator for Package 8C. It runs all 10 intelligence engines in a coordinated pipeline and produces a unified intelligence dashboard.

## Singleton Access

```python
from sfc.narrative.command_center import get_narrative_command_center

center = get_narrative_command_center()
```

## Full Intelligence Run

```python
dashboard = await center.run_full_intelligence(context={})
```

Returns a dict containing:

| Key | Description |
|-----|-------------|
| `narrative_map` | All active narratives and relationships |
| `lifecycle_batch` | Stage analysis for top 5 narratives |
| `forecast_bundle` | Multi-horizon forecasts |
| `risk_reports` | Risk assessments for top 3 narratives |
| `strategy_reports` | Strategy recommendations |
| `audience_model_report` | Digital twin analysis |
| `segment_report` | Audience cluster segmentation |
| `evolution_report` | Growth and retention forecasts |
| `influence_network` | Media influence map |
| `war_room_escalations` | Narratives requiring war room activation |
| `total_narratives` | Active narrative count |
| `total_audience` | Total modeled audience |
| `summary` | Executive one-liner summary |

## Scenario Simulation

```python
result = await center.simulate_scenario(
    scenario_name="transfer_announcement",
    narrative_id="optional_narrative_id",
    context={"player": "player_name"},
)
```

## System Status

```python
status = center.get_status()
# {
#   "status": "active",
#   "engines": {
#     "narrative_modeling": "ready",
#     "narrative_lifecycle": "ready",
#     ... all 10 engines ...
#   }
# }
```

## War Room Integration

When any narrative's risk score exceeds 70, the command center flags it in `war_room_escalations`. These should be routed through the main `governance_node` in the LangGraph pipeline for executive review.

## Pipeline Stage

The `narrative_command_center_node` runs the full intelligence pipeline and writes its output to `state["narrative_command_center"]`. It is a standalone analytics node — it does not publish content and does not bypass governance.
