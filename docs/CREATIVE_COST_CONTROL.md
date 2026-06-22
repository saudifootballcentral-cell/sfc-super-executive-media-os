# Creative Cost Control

## Master Switch

`GENERATE_REAL_ASSETS=false` (default) — no provider calls, no cost.

Set to `true` only in production or intentional testing.

---

## Budget Limits

| Variable | Default | Scope |
|---|---|---|
| `CREATIVE_PER_RUN_BUDGET_USD` | `5.00` | Max spend per orchestration run |
| `CREATIVE_DAILY_BUDGET_USD` | `50.00` | Max spend per calendar day |

When a provider call would push either budget over its limit, the call is blocked
and `GeneratedAsset.status = provider_unavailable` is returned with
`metadata.reason = "budget_exceeded"`.

---

## Provider Cost Estimates

| Provider | Estimated Cost (USD) |
|---|---|
| `openai_image` | $0.04 |
| `ideogram` | $0.08 |
| `flux` | $0.003 |
| `elevenlabs` | $0.01 |
| `azure_voice` | $0.005 |

These are approximate; actual billing depends on image size and audio length.

---

## Cost Tracking

```python
from sfc.creative.providers.cost_guard import get_cost_guard

guard = get_cost_guard()
print("Today's spend:", guard.daily_total())
print("Run spend:", guard.run_total("run-id"))
print("Asset log:", guard.asset_log())
```

Costs are recorded in-process only. Restart resets all counters.
For persistent tracking, write `guard.asset_log()` to a database at run end.

---

## Disabling Expensive Providers

To use only cheap providers, unset the expensive provider's API key:

```bash
unset OPENAI_API_KEY   # skip DALL-E ($0.04)
unset IDEOGRAM_API_KEY  # skip Ideogram ($0.08)
# Flux ($0.003) will be tried instead
```

---

## Retry Behaviour

Each provider gets up to 2 retries with exponential backoff (0.5s, 1.0s).
Timeout per attempt: 120s for images, 120s for audio.
Budget is only charged on success.
