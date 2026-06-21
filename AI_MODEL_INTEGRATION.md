# AI Model Integration — SFC Super Executive Media OS

## Architecture Overview

Package 7 introduces a 3-provider AI gateway that enhances the existing 14-node LangGraph pipeline without replacing any existing logic. All AI calls are optional enhancements; every node continues to work without any API keys.

```
Incoming Request
      │
      ▼
 AIGateway.complete()
      │
      ├── ModelPolicy.select()          → choose provider + model
      ├── CostTracker.check_budget()    → enforce MAX_DAILY_AI_COST
      ├── Primary Provider attempt      → claude / openai / gemini
      ├── Fallback Provider attempt     → if primary fails
      ├── FallbackManager.get_fallback() → if all AI fails
      └── validate_output()            → Pydantic validation if schema set
```

## Provider Hierarchy

```
1. Primary provider  (per ModelPolicy rule — usually Claude)
2. Fallback provider (per ModelPolicy rule — e.g., OpenAI gpt-4o-mini)
3. Deterministic fallback (FallbackManager — always works, zero cost)
```

The gateway **never raises exceptions**. It always returns a `ModelResponse` object.

## Package Structure

```
src/sfc/ai/
├── __init__.py              — exports: get_ai_gateway, AIGateway, ModelPolicy, ModelRequest, ModelResponse
├── model_gateway.py         — AIGateway (process-level singleton)
├── model_policy.py          — ModelPolicy + PolicyRule dataclass
├── models.py                — ModelRequest, ModelResponse (Pydantic v2)
├── prompt_loader.py         — PromptLoader (process-level singleton)
├── structured_output.py     — Pydantic output models + extract_json/validate_output
├── cost_tracker.py          — CostTracker (process-level singleton)
├── fallback_manager.py      — FallbackManager (deterministic fallbacks)
└── providers/
    ├── base.py              — AIProvider ABC
    ├── claude.py            — ClaudeProvider (anthropic library)
    ├── openai_provider.py   — OpenAIProvider (lazy import)
    └── gemini_provider.py   — GeminiProvider (lazy import)
```

## Node-by-Node AI Usage

| Node | task_type | AI Role | Schema |
|------|-----------|---------|--------|
| super_executive | executive | Executive decision-making | ExecutiveDecisionAI |
| strategic_planning | strategic_planning | Execution plan generation | (JSON) |
| intelligence | intelligence | Key facts enrichment | IntelligenceReportAI |
| editorial | editorial | First draft title + body | ContentDraftAI |
| creative | creative | Creative brief concept | CreativeBriefAI |
| governance | governance | Explanatory notes only | (JSON) |
| persona_layer | persona | Persona synthesis insight | (JSON) |
| revenue_node | revenue | Revenue signal prioritization | (JSON) |
| learning | learning | Pattern + lesson extraction | LearningExtractionAI |

## Fallback Chain

Every node follows this pattern:

```python
# 1. Try AI gateway (if API key available)
try:
    ai_response = await gateway.complete(request)
    if ai_response.success and not ai_response.used_fallback:
        return _build_from_ai(ai_response)
except Exception:
    pass

# 2. Try existing division service (Package 2 integration)
try:
    result = await service.execute(...)
    if result.success:
        return result.data
except Exception:
    pass

# 3. Deterministic stub logic (always works)
return _stub_fallback(state)
```

## Governance Protection (CRITICAL)

The AI **cannot** override constitutional compliance decisions.

In `governance_node.py`:
1. `_review_draft()` is called for every content item — this is code-based, not AI
2. Approval/rejection is determined solely by the code check
3. The AI call runs **after** the code check, generates explanatory notes only
4. AI output is stored in `ai_governance_notes` — never in `approved_content`

The following are **always enforced by code**:
- `source_count >= 2` (Verification Policy)
- `confidence_score >= 85` (Confidence Policy)
- `brand_alignment_score >= 70` (Brand Alignment)
- Rumor labeling when `is_rumor=True`

## How to Add a New Provider

1. Create `src/sfc/ai/providers/my_provider.py` extending `AIProvider`
2. Implement `complete()`, `is_available()`, `health_check()`
3. Use lazy imports for optional libraries
4. Add provider to `AIGateway._get_provider()` switch
5. Add policy rules in `model_policy.py` referencing the new provider name
6. Set the corresponding API key env var
