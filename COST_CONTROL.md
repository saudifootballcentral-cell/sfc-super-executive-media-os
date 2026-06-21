# Cost Control — SFC Super Executive Media OS

## Cost Model per Provider

### Claude (Anthropic)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical use |
|-------|-----------------------|------------------------|-------------|
| claude-opus-4-8 | $15.00 | $75.00 | Executive decisions only |
| claude-sonnet-4-6 | $3.00 | $15.00 | Editorial, intelligence, creative, governance |
| claude-haiku-4-5-20251001 | $0.25 | $1.25 | Persona, revenue, learning, routing |

### OpenAI

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical use |
|-------|-----------------------|------------------------|-------------|
| gpt-4o | $5.00 | $15.00 | High-quality fallback |
| gpt-4o-mini | $0.15 | $0.60 | Low-cost editorial/creative fallback |

### Google Gemini

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical use |
|-------|-----------------------|------------------------|-------------|
| gemini-1.5-flash | $0.075 | $0.30 | Ultra-cheap summary fallback |
| gemini-1.5-pro | $3.50 | $10.50 | High-quality Gemini fallback |

## How CostTracker Works

The `CostTracker` is a process-level singleton that records every AI call:

```python
from sfc.ai.cost_tracker import get_cost_tracker

tracker = get_cost_tracker()

# After a pipeline run:
report = tracker.get_report()
print(f"Total spend: ${report['session_total_usd']:.4f}")
print(f"Model breakdown: {report['model_breakdown_usd']}")
print(f"Within budget: {report['within_budget']}")
```

Each `CallRecord` stores:
- timestamp, task_type, provider, model
- input_tokens, output_tokens, cost_usd, latency_ms
- success, used_fallback, validation_failed

## MAX_DAILY_AI_COST Enforcement

The budget is checked **before each AI call** in `AIGateway.complete()`:

```python
if not cost_tracker.check_budget():
    # Skip AI call entirely
    return fallback_manager.get_fallback(request)
```

When the budget is exceeded:
1. No further AI API calls are made
2. `FallbackManager` returns deterministic responses
3. The pipeline continues normally — no errors raised
4. `used_fallback=True` is set on all responses

Set the budget:
```bash
export MAX_DAILY_AI_COST=100.0  # Default: $100
export MAX_DAILY_AI_COST=0      # Disable all AI calls (pure deterministic mode)
export MAX_DAILY_AI_COST=1000   # Higher limit for production
```

## Cost Breakdown by Node (Estimated per Pipeline Run)

Assuming average token counts per call:

| Node | Model | Estimated tokens | Estimated cost |
|------|-------|-----------------|----------------|
| super_executive | claude-opus-4-8 | ~2K in / ~500 out | $0.067 |
| strategic_planning | claude-sonnet-4-6 | ~1K in / ~400 out | $0.009 |
| intelligence | claude-sonnet-4-6 | ~800 in / ~300 out | $0.007 |
| editorial | claude-sonnet-4-6 | ~1.5K in / ~800 out | $0.016 |
| creative | claude-sonnet-4-6 | ~600 in / ~300 out | $0.006 |
| governance | claude-sonnet-4-6 | ~400 in / ~200 out | $0.004 |
| persona_layer | claude-haiku-4-5-20251001 | ~300 in / ~200 out | $0.00033 |
| revenue_node | claude-haiku-4-5-20251001 | ~400 in / ~200 out | $0.00035 |
| learning | claude-haiku-4-5-20251001 | ~500 in / ~200 out | $0.00038 |
| **Total (estimated)** | | | **~$0.11 / run** |

With `cost_optimized` policy (executive uses Sonnet instead of Opus): ~$0.05 / run

## Optimization Recommendations

### 1. Use cost_optimized policy for routine tasks
```bash
export DEFAULT_MODEL_POLICY=cost_optimized
```
Reduces cost by ~50% with minimal quality impact for standard news/match tasks.

### 2. Reserve Opus for crisis/high-stakes decisions only
The default policy already does this — Opus is only used for `executive` task_type.

### 3. Monitor model breakdown regularly
```python
tracker = get_cost_tracker()
breakdown = tracker.get_model_breakdown()
# {"claude-opus-4-8": 0.067, "claude-sonnet-4-6": 0.042, ...}
```

### 4. Use Haiku for high-volume operations
Tasks like `persona`, `learning`, `routing` use Haiku (40x cheaper than Sonnet per 1M tokens).

### 5. Set a conservative MAX_DAILY_AI_COST
```bash
export MAX_DAILY_AI_COST=10.0  # For development
export MAX_DAILY_AI_COST=100.0  # For production
```

### 6. Deterministic fallbacks have zero cost
When AI is unavailable or budget exceeded, `FallbackManager` responses cost $0.00 and complete in <1ms.
