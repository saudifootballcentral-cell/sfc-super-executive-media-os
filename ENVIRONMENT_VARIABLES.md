# Environment Variables — SFC Super Executive Media OS

All environment variables used by Package 7 AI Model Integration.

## API Keys

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Recommended | Enables Claude providers. Without this, all nodes use deterministic fallbacks. |
| `OPENAI_API_KEY` | Optional | Enables OpenAI fallback provider (gpt-4o-mini, gpt-4o). |
| `GEMINI_API_KEY` | Optional | Enables Gemini fallback provider (gemini-1.5-flash, gemini-1.5-pro). |

When no API keys are set, the system works fully via deterministic fallbacks. No errors are raised.

## Model Policy

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL_POLICY` | `claude_primary` | Sets the model selection strategy. Options: `claude_primary`, `openai_primary`, `cost_optimized`, `performance`. |

## Budget Control

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DAILY_AI_COST` | `100.0` | Maximum AI spend in USD per session. When exceeded, all calls fall back to deterministic responses. Set to `0` to disable all AI calls. |

## Provider Behavior

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_TIMEOUT_SECONDS` | `30` | Maximum seconds to wait for an AI provider response before timing out. Applies to Claude, OpenAI, and Gemini. |
| `AI_MAX_RETRIES` | `3` | Number of retry attempts with exponential backoff when a provider call fails. Backoff: 1s, 2s, 4s. |

## Path Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SFC_REPO_ROOT` | Auto-detected | Optional override for the repository root path used by PromptLoader. Auto-detected from `Path(__file__).parents[3]` relative to `src/sfc/ai/prompt_loader.py`. |

## Usage Examples

### Minimal setup (Claude only)
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

### Full multi-provider setup
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=AI...
export DEFAULT_MODEL_POLICY=claude_primary
export MAX_DAILY_AI_COST=50.0
export AI_TIMEOUT_SECONDS=30
export AI_MAX_RETRIES=3
python main.py
```

### Cost-optimized CI/CD setup
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export DEFAULT_MODEL_POLICY=cost_optimized
export MAX_DAILY_AI_COST=5.0
export AI_TIMEOUT_SECONDS=15
export AI_MAX_RETRIES=1
pytest tests/
```

### No API keys (test mode — fully deterministic)
```bash
# No API keys set
pytest tests/  # All 900+ tests pass
python main.py  # System runs via deterministic fallbacks
```
