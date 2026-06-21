# Model Policy — SFC Super Executive Media OS

## Policy Rules Table

| task_type | Provider | Model | Fallback Provider | Fallback Model | Max Tokens | Temp |
|-----------|----------|-------|-------------------|----------------|------------|------|
| executive | claude | claude-opus-4-8 | claude | claude-sonnet-4-6 | 2048 | 0.3 |
| governance | claude | claude-sonnet-4-6 | claude | claude-haiku-4-5-20251001 | 1024 | 0.1 |
| editorial | claude | claude-sonnet-4-6 | openai | gpt-4o-mini | 4096 | 0.7 |
| intelligence | claude | claude-sonnet-4-6 | claude | claude-haiku-4-5-20251001 | 2048 | 0.3 |
| creative | claude | claude-sonnet-4-6 | openai | gpt-4o-mini | 2048 | 0.8 |
| strategic_planning | claude | claude-sonnet-4-6 | claude | claude-haiku-4-5-20251001 | 2048 | 0.5 |
| persona | claude | claude-haiku-4-5-20251001 | claude | claude-haiku-4-5-20251001 | 1024 | 0.7 |
| revenue | claude | claude-haiku-4-5-20251001 | claude | claude-haiku-4-5-20251001 | 1024 | 0.3 |
| learning | claude | claude-haiku-4-5-20251001 | claude | claude-haiku-4-5-20251001 | 1024 | 0.5 |
| routing | claude | claude-haiku-4-5-20251001 | claude | claude-haiku-4-5-20251001 | 512 | 0.1 |
| summary | claude | claude-haiku-4-5-20251001 | gemini | gemini-1.5-flash | 512 | 0.5 |
| default | claude | claude-sonnet-4-6 | claude | claude-haiku-4-5-20251001 | 2048 | 0.7 |

## How to Override via Environment

Set `DEFAULT_MODEL_POLICY` to one of:

| Value | Description |
|-------|-------------|
| `claude_primary` (default) | All tasks use Claude as primary provider |
| `openai_primary` | Editorial and creative tasks use OpenAI GPT-4o |
| `cost_optimized` | Executive uses Sonnet instead of Opus; editorial uses Haiku |
| `performance` | Editorial and intelligence use Opus for highest quality |

Example:
```bash
export DEFAULT_MODEL_POLICY=cost_optimized
```

## When Fallback Triggers

The fallback provider is tried when the primary provider:
- Returns `success=False` (API error, rate limit, etc.)
- Raises an exception
- Returns an empty or unparseable response

The deterministic fallback (`FallbackManager`) is used when:
- Both primary and fallback providers fail
- `MAX_DAILY_AI_COST` budget is exceeded
- No API keys are configured

## Cost Optimization Strategies

### Use `cost_optimized` policy
Switches executive from Opus ($15/$75 per 1M) to Sonnet ($3/$15 per 1M):
- ~80% cost reduction on executive decisions
- Minimal quality impact for routine tasks

### Use Haiku for high-volume tasks
Tasks like `routing`, `persona`, `learning` already use Haiku by default:
- Haiku: $0.25/$1.25 per 1M tokens
- vs Sonnet: $3/$15 per 1M tokens

### Monitor via CostTracker
```python
from sfc.ai.cost_tracker import get_cost_tracker
report = get_cost_tracker().get_report()
print(report["model_breakdown_usd"])  # Cost per model
print(report["session_total_usd"])    # Total session cost
```

### Set conservative budget limit
```bash
export MAX_DAILY_AI_COST=10.0  # $10/day limit
```

The gateway automatically switches to deterministic fallbacks when the limit is reached.
