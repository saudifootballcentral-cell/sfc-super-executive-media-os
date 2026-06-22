# Creative Provider Setup

## Prerequisites

All credentials must be passed via environment variables. Never hardcode secrets.

---

## Image Providers

### OpenAI Image (DALL-E 3)

```bash
export OPENAI_API_KEY="sk-..."
export GENERATE_REAL_ASSETS="true"
```

Cost: ~$0.04 per image. Model: `dall-e-3`.

### Flux (Black Forest Labs)

```bash
export FLUX_API_KEY="..."
export GENERATE_REAL_ASSETS="true"
```

Cost: ~$0.003 per image. Endpoint: `https://api.bfl.ml/v1/flux-pro-1.1`.

### Ideogram

```bash
export IDEOGRAM_API_KEY="..."
export GENERATE_REAL_ASSETS="true"
```

Cost: ~$0.08 per image. Model: `V_2`.

---

## Audio Providers

### ElevenLabs

```bash
export ELEVENLABS_API_KEY="..."
# Optional: override default voice IDs
export ELEVENLABS_ARABIC_VOICE_ID="..."
export ELEVENLABS_ENGLISH_VOICE_ID="..."
export GENERATE_REAL_ASSETS="true"
```

Cost: ~$0.01 per request. Model: `eleven_multilingual_v2`.

### Azure Cognitive Speech

Both key AND region must be set.

```bash
export AZURE_SPEECH_KEY="..."
export AZURE_SPEECH_REGION="eastus"
export GENERATE_REAL_ASSETS="true"
```

Cost: ~$0.005 per request. Output: 24kHz MP3.

---

## Provider Priority

If multiple providers are configured, the chain tries them in priority order:

**Image:** OpenAI → Flux → Ideogram  
**Audio:** ElevenLabs → Azure Voice

The first provider that returns a valid file wins. Subsequent providers are not called.

---

## Dry-run vs. Real Generation

| Env | Behaviour |
|---|---|
| `GENERATE_REAL_ASSETS=false` (default) | Planning mode — returns mock URLs, no API calls, no cost |
| `GENERATE_REAL_ASSETS=true` | Real generation — calls providers, saves files, records costs |

To test provider connectivity without incurring production cost, set a low `CREATIVE_PER_RUN_BUDGET_USD` first.

---

## Verifying a Provider

```python
from sfc.creative.providers.image_providers import get_image_provider_chain
import asyncio, os

os.environ["GENERATE_REAL_ASSETS"] = "true"
os.environ["OPENAI_API_KEY"] = "sk-..."

async def test():
    chain = get_image_provider_chain()
    print("Available:", chain.available_providers())
    asset = await chain.generate("Saudi football match", "1024x1024")
    print("Status:", asset.status)
    print("Path:", asset.local_path)

asyncio.run(test())
```
