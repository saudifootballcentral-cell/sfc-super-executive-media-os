# Package 10B — Real Creative Providers

## Overview

Package 10B replaces mock asset URLs in the Creative Production Layer with real
provider-backed generation and explicit `provider_unavailable` states.

The existing Creative Production Layer is **not rebuilt**. All factory services
(ImageFactory, ThumbnailFactory, AudioFactory) continue to work exactly as before
when `GENERATE_REAL_ASSETS=false` (the safe default). Real generation is activated
only by setting `GENERATE_REAL_ASSETS=true` in the environment.

---

## New module: `src/sfc/creative/providers/`

| File | Purpose |
|---|---|
| `generated_asset.py` | `GeneratedAsset` model — source of truth for real file generation |
| `asset_storage.py` | `LocalAssetStorage` — save files, compute checksums, write manifests |
| `cost_guard.py` | `CostGuard` — per-run and daily budget enforcement |
| `retry.py` | `RetryExecutor` — exponential backoff retry for provider calls |
| `image_providers.py` | `ImageProviderChain` + OpenAI/Flux/Ideogram providers |
| `audio_providers.py` | `AudioProviderChain` + ElevenLabs/AzureVoice providers |

---

## Provider Chains

### Image: `ImageProviderChain`

Priority order:
1. `OpenAIImageProvider` — requires `OPENAI_API_KEY`
2. `FluxProvider` — requires `FLUX_API_KEY`
3. `IdeogramProvider` — requires `IDEOGRAM_API_KEY`
4. Returns `provider_unavailable` if none configured

### Audio: `AudioProviderChain`

Priority order:
1. `ElevenLabsProvider` — requires `ELEVENLABS_API_KEY`
2. `AzureVoiceProvider` — requires `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`
3. Returns `provider_unavailable` if none configured

---

## GeneratedAsset Model

```python
class GeneratedAsset(BaseModel):
    asset_id: str
    asset_type: str           # image | thumbnail | audio
    provider: str
    status: GeneratedAssetStatus
    local_path: str           # path to saved file on disk
    public_url: str | None    # only if CREATIVE_PUBLIC_BASE_URL is set
    mime_type: str
    file_size: int
    checksum_sha256: str
    prompt: str
    negative_prompt: str
    created_at: datetime
    cost_estimate: float
    quality_score: float
    governance_status: GovernanceStatus
    metadata: dict
```

### Status values

| Status | Meaning |
|---|---|
| `generated` | Real file saved; `local_path`, `checksum_sha256`, `file_size` all populated |
| `provider_unavailable` | No credentials configured OR `GENERATE_REAL_ASSETS=false` |
| `failed` | Credentials exist but all providers errored |
| `rejected` | File failed QC validation |
| `pending_review` | Awaiting governance sign-off |

---

## Integration with Existing Factories

When `GENERATE_REAL_ASSETS=false` (default), factory services are **unchanged**:
- `ImageFactoryService` returns `ImageVariant` with planning mock URLs
- `ThumbnailFactoryService` returns `ThumbnailVariant` with planning mock URLs
- `AudioFactoryService` returns `AudioAsset` with planning mock URLs

When `GENERATE_REAL_ASSETS=true`:
- Provider chain is called for each variant
- On success: `file_url` is set to the real `local_path`
- On failure/unavailable: `file_url` is set to `""` (no fake URL)

---

## Content Packaging Validation

`ContentPackagingService.validate_asset_for_packaging(asset)` enforces:

- `status == generated`
- `quality_score >= 70.0`
- `governance_status in (approved, pending_review)`
- `local_path` is set and file exists on disk
- `file_size > 0`
- `checksum_sha256` is non-empty

`ContentPackagingService.package_from_generated_assets(package_type, title, assets)` —
validates all assets before packaging; raises `ValueError` if none pass.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `GENERATE_REAL_ASSETS` | `false` | Master switch; set to `true` to enable provider calls |
| `DRY_RUN_CREATIVE` | `true` | Alias for dry-run planning mode |
| `CREATIVE_STORAGE_PATH` | `./artifacts/creative` | Root for saved files |
| `CREATIVE_PUBLIC_BASE_URL` | `""` | If set, `public_url` is built from this base |
| `CREATIVE_PER_RUN_BUDGET_USD` | `5.0` | Max spend per run |
| `CREATIVE_DAILY_BUDGET_USD` | `50.0` | Max spend per day |
| `OPENAI_API_KEY` | — | OpenAI Image provider |
| `FLUX_API_KEY` | — | Flux provider |
| `IDEOGRAM_API_KEY` | — | Ideogram provider |
| `ELEVENLABS_API_KEY` | — | ElevenLabs TTS provider |
| `AZURE_SPEECH_KEY` | — | Azure Cognitive Speech |
| `AZURE_SPEECH_REGION` | — | Azure region (e.g. `eastus`) |
