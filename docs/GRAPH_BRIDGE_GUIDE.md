# GraphBridge — Composing Existing Graphs

## Purpose

`GraphBridge` provides a uniform async interface over each compiled LangGraph graph. It is the mechanism by which the orchestrator composes the existing graphs without rebuilding them.

## Managed Graphs

| Graph name | Module | Description |
|---|---|---|
| `main_graph` | `sfc.graph.graph` | Core 14-node pipeline |
| `social_intelligence_graph` | `sfc.graph.social_intelligence_graph` | 21-node 8B+8C intelligence |
| `creative_production_graph` | `sfc.graph.creative_production_graph` | 10-node 8E asset generation |
| `publishing_connectors_graph` | `sfc.graph.publishing_connectors_graph` | 4-node 9A connectors |

## API

```python
bridge = GraphBridge()

result = await bridge.execute(
    graph_name="social_intelligence_graph",
    run_id="abc123",
    task_type="social_scan",
    task_payload={},
    prior_state=None,          # optional: overlay keys from prior graph run
)
# result is a full SFCState dict
```

## State Threading

The orchestrator threads state between graph runs via `prior_state`:

```
social_intelligence_graph → result stored in master_state.graph_states["social_intelligence_graph"]
  ↓ (social_intelligence_report, trend_radar_data, narrative_intelligence_data, fan_sentiment_data)
main_graph ← these keys overlaid on initial SFCState
```

## Graph Loading

Graphs are built lazily on first call and cached in-process. All graphs support LangGraph's `ainvoke()` interface and are called with a fresh `SFCState` initialized by `make_initial_state()`.

## Event Publishing

After each successful graph execution, `GraphBridge` publishes the appropriate orchestration event:

| Graph | Event |
|---|---|
| `social_intelligence_graph` | `SocialIntelligenceRunCompleted` |
| `creative_production_graph` | `CreativeProductionRunCompleted` |
| `publishing_connectors_graph` | `ConnectorRunCompleted` |
| `main_graph` | `StageCompleted` |

## Error Handling

On failure, `GraphBridge.execute()` raises `GraphBridgeError`. The `WorkflowRunner` catches this and delegates to `RecoveryEngine` for retry logic.
