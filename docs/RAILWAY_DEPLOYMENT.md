# Railway Deployment — SFC Super Executive Media OS

## Deployment method

Railway Docker via root `Dockerfile`.  
Nixpacks is not used — the project requires `ffmpeg`/`ffprobe` system packages.

## Quick start

1. Connect the repository to Railway.
2. Railway auto-detects `Dockerfile` at the repo root.
3. Set the required environment variables in Railway's service settings (see below).
4. Deploy.

The `railway.toml` at the repo root configures the builder and start command automatically.

## Production start command

```
python scripts/railway_worker.py
```

`scripts/railway_worker.py` is the production entrypoint. It:
- Verifies `ffmpeg` and `ffprobe` availability (exits 1 on failure)
- Verifies all `sfc` package imports
- Instantiates `MasterOrchestrator` in dry-run mode by default
- Logs startup success
- Logs a heartbeat every 60 seconds to confirm the worker is alive
- Never publishes unless `LIVE_PUBLISHING_ENABLED=true` is explicitly set

`scripts/run_demo.py` is a development helper that runs a one-shot scenario and exits. Do not use it as the Railway start command.

---

## Environment variables

### AI providers

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Recommended | — | Enables Claude models. Without it, deterministic fallbacks are used. |
| `OPENAI_API_KEY` | Optional | — | Enables OpenAI fallback (gpt-4o-mini, gpt-4o). |
| `GEMINI_API_KEY` | Optional | — | Enables Gemini fallback (gemini-1.5-flash, gemini-1.5-pro). |
| `ELEVENLABS_API_KEY` | Optional | — | Enables ElevenLabs TTS for podcast/audio generation. |

### Buffer publishing

| Variable | Required | Default | Description |
|---|---|---|---|
| `BUFFER_ACCESS_TOKEN` | Required for publishing | — | Buffer API personal access token. Obtain from buffer.com → Settings → Apps. |
| `LIVE_PUBLISHING_ENABLED` | Optional | `false` | **Set `true` only when real social publishing is intended.** `false` = dry-run, no posts sent. |

### Asset generation

| Variable | Required | Default | Description |
|---|---|---|---|
| `GENERATE_REAL_ASSETS` | Optional | `false` | `true` calls real image/audio AI providers and incurs cost. |
| `VIDEO_PROCESSING_ENABLED` | Optional | `false` | `true` activates ffmpeg clipping/enhancement. Requires video source files. |

### Cost control

| Variable | Required | Default | Description |
|---|---|---|---|
| `MAX_DAILY_AI_COST` | Optional | `100.0` | Maximum AI spend in USD per session. Set `0` to disable all AI calls. |
| `DEFAULT_MODEL_POLICY` | Optional | `claude_primary` | Model selection strategy: `claude_primary`, `openai_primary`, `cost_optimized`, `performance`. |

### Buffer profile IDs (optional overrides)

These skip the `profiles.json` API call and are useful when profile IDs are known in advance.

| Variable | Platform |
|---|---|
| `BUFFER_X_PROFILE_ID` | X (Twitter) |
| `BUFFER_YOUTUBE_PROFILE_ID` | YouTube |
| `BUFFER_INSTAGRAM_PROFILE_ID` | Instagram |
| `BUFFER_TIKTOK_PROFILE_ID` | TikTok |
| `BUFFER_LINKEDIN_PROFILE_ID` | LinkedIn |
| `BUFFER_FACEBOOK_PROFILE_ID` | Facebook |
| `BUFFER_THREADS_PROFILE_ID` | Threads |

---

## Safe defaults (baked into Dockerfile)

These env vars are set in the `Dockerfile` `ENV` directives and act as defaults if not overridden:

```
LIVE_PUBLISHING_ENABLED=false
GENERATE_REAL_ASSETS=false
VIDEO_PROCESSING_ENABLED=false
```

**Do not override these to `true` without understanding the consequences:**
- `LIVE_PUBLISHING_ENABLED=true` will post content to real social media accounts.
- `GENERATE_REAL_ASSETS=true` will call paid AI image/audio APIs.
- `VIDEO_PROCESSING_ENABLED=true` requires actual video files to be accessible.

---

## System packages in the image

The production image installs:

| Package | Why |
|---|---|
| `ffmpeg` | Video clipping (`SmartClippingEngine`), aspect-ratio re-encoding (`ClipEnhancementEngine`) |
| `ffprobe` | Video metadata extraction (`VideoIngestionService`) — bundled with ffmpeg |

Without these, `Video Intelligence` gracefully degrades to dry-run mode (`FFMPEG_AVAILABLE = False`).

---

## Runtime artifact directories

The image creates these directories at build time:

```
/app/artifacts/creative/
/app/artifacts/video_intelligence/
/app/artifacts/analytics_sync/
```

These are excluded from git via `.gitignore`. On Railway, they live inside the container filesystem and are ephemeral. Mount a Railway volume at `/app/artifacts` if persistence across deploys is needed.

---

## Health check

The `HEALTHCHECK` directive in the `Dockerfile` runs `scripts/healthcheck.py` every 30 seconds:

- `ffmpeg` binary present
- `ffprobe` binary present
- `build_graph()` succeeds
- `MasterOrchestrator` imports cleanly
- `BufferAPIClient` instantiates
- `video_intelligence` modules import

---

## Deployment files reference

| File | Purpose |
|---|---|
| `Dockerfile` | Root-level production image (Railway auto-detected) |
| `railway.toml` | Railway builder + start command config |
| `scripts/healthcheck.py` | Health check called by Docker HEALTHCHECK |
| `deployment/docker/Dockerfile` | Original multi-service Dockerfile (used by docker-compose) |
| `deployment/docker/docker-compose.yml` | Local dev stack with Redis + Postgres |

---

## Minimum viable Railway deploy (dry-run, no live publishing)

Set only:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Everything else defaults to safe dry-run mode.
