# Package 8D — Social & Narrative Intelligence Graph

Unified LangGraph pipeline wiring all Package 8B (Social Intelligence) and
Package 8C (Narrative Intelligence & Audience Modeling) nodes into a single
sequential scan that runs on a schedule independently of the main content
production pipeline.

## Pipeline overview

```
[START]
  │
  ▼
social_intelligence       ← 8B: Full social scan orchestrator
  │
trend_radar               ← 8B: Top trends by velocity and reach
  │
fan_sentiment             ← 8B: Real-time fan mood across platforms
  │
narrative_intelligence    ← 8B: Social narrative detection
  │
influencer_intelligence   ← 8B: Influencer mapping and classification
  │
virality_prediction       ← 8B: Content virality forecast
  │
audience_intelligence     ← 8B: Audience segment intelligence
  │
opportunity_detection     ← 8B: Content opportunity scoring
  │
social_war_room           ← 8B: Social crisis triage and activation
  │  [8B → 8C handoff]
narrative_modeling        ← 8C: Deep narrative profiling (NarrativeMap)
  │
narrative_lifecycle_step  ← 8C: Stage analysis (SEED→DEAD)
  │
narrative_forecasting     ← 8C: 24h/72h/7d/30d/90d forecasts
  │
narrative_risk_step       ← 8C: 7-type risk scoring + war room flags
  │
narrative_strategy_step   ← 8C: Strategy actions (AMPLIFY/COUNTER/etc)
  │
audience_modeling         ← 8C: Digital twins for 7 audience types
  │
audience_segmentation     ← 8C: 8-cluster audience segments
  │
audience_evolution_step   ← 8C: Growth/retention + platform migration
  │
influence_network_step    ← 8C: 12-node Saudi football media map
  │
reaction_simulator        ← 8C: Scenario-based reaction forecasting
  │
narrative_command_center_step ← 8C: Full intelligence dashboard
  │
memory_update             ← Persists all intelligence to memory layers
  │
[END]
```

Total: **21 nodes** (9 Package 8B + 11 Package 8C + 1 memory_update).

## Node naming convention

Six Package 8C node aliases carry a `_step` suffix to avoid LangGraph's
restriction that node names must not match `SFCState` TypedDict key names:

| Graph node alias              | SFCState key               |
|-------------------------------|----------------------------|
| `narrative_lifecycle_step`    | `narrative_lifecycle`      |
| `narrative_risk_step`         | `narrative_risk`           |
| `narrative_strategy_step`     | `narrative_strategy`       |
| `audience_evolution_step`     | `audience_evolution`       |
| `influence_network_step`      | `influence_network`        |
| `narrative_command_center_step` | `narrative_command_center` |

The underlying node functions are unchanged; only the graph alias differs.

## Usage

```python
from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
from sfc.graph.state import make_initial_state

graph = build_social_intelligence_graph()

initial_state = make_initial_state("social_intelligence_scan", {
    "scenario": "transfer_announcement",  # optional — used by reaction_simulator
})

result = await graph.ainvoke(initial_state)

# Package 8B outputs
trend_data       = result["trend_radar_data"]
sentiment_data   = result["fan_sentiment_data"]
war_room_state   = result["social_war_room_state"]

# Package 8C outputs
narrative_map    = result["narrative_models"]
lifecycle        = result["narrative_lifecycle"]
forecasts        = result["narrative_forecast"]
risk             = result["narrative_risk"]
strategy         = result["narrative_strategy"]
audience_twins   = result["audience_models"]
segments         = result["audience_segments"]
evolution        = result["audience_evolution"]
network          = result["influence_network"]
reaction         = result["reaction_forecast"]
command_center   = result["narrative_command_center"]
```

## Scheduling

This graph is designed to run on a schedule — hourly or at match-day
intervals — using a LangGraph scheduler, Celery beat, or any cron-like
mechanism. Pass an optional `checkpointer` to enable state persistence
between runs:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("sfc_checkpoints.db") as saver:
    graph = build_social_intelligence_graph(checkpointer=saver)
    result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "scan_001"}})
```

## Governance

**This pipeline is READ-ONLY intelligence.** No content is published from
this graph. All outputs are analytics and forecasts stored in `SFCState`.

War room activations or escalations detected by `narrative_risk_step` or
`social_war_room` **must route through the main pipeline** (`graph.py`)
governance gate before any action is taken. The `requires_war_room` flag
in risk reports is informational — it does not trigger any action from
within this pipeline.

## State outputs written

All 21 nodes write to dedicated `SFCState` keys so outputs are available
across the session:

| SFCState key                  | Written by                    |
|-------------------------------|-------------------------------|
| `social_intelligence_report`  | `social_intelligence`         |
| `trend_radar_data`            | `trend_radar`                 |
| `fan_sentiment_data`          | `fan_sentiment`               |
| `narrative_intelligence_data` | `narrative_intelligence`      |
| `influencer_data`             | `influencer_intelligence`     |
| `virality_forecast`           | `virality_prediction`         |
| `audience_intelligence_data`  | `audience_intelligence`       |
| `opportunity_detections`      | `opportunity_detection`       |
| `social_war_room_state`       | `social_war_room`             |
| `narrative_models`            | `narrative_modeling`          |
| `narrative_lifecycle`         | `narrative_lifecycle_step`    |
| `narrative_forecast`          | `narrative_forecasting`       |
| `narrative_risk`              | `narrative_risk_step`         |
| `narrative_strategy`          | `narrative_strategy_step`     |
| `audience_models`             | `audience_modeling`           |
| `audience_segments`           | `audience_segmentation`       |
| `audience_evolution`          | `audience_evolution_step`     |
| `influence_network`           | `influence_network_step`      |
| `reaction_forecast`           | `reaction_simulator`          |
| `narrative_command_center`    | `narrative_command_center_step` |

## Error handling

Every node wraps its logic in `try/except`. On failure the node returns a
safe partial result and appends a warning to `state["warnings"]`. This
ensures the pipeline always completes — a single node failure will not
halt the downstream chain.
