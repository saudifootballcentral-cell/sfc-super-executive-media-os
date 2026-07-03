# Pipeline — Meshy (AI asset generation)

Stage: `meshy_generation` · Owner: concept-artist (with character/prop/texture artists)

## Flow
1. Routing decision exists (`/siraj-route`, logged with `--log`). No decision, no spend.
2. Prompt discipline: always "low poly, game asset, clean topology"; characters add
   "T-pose, symmetrical"; style-guide keywords always included.
3. `python3 ~/meshy/meshy_client.py text "<prompt>" --name <Name> --polys <budget>`
   (or `image` / `retexture`). Fire ALL Meshy jobs first — cloud time is free time;
   poll while building procedural assets and writing C#.
4. Preview verdict before refine: wrong silhouette → fix prompt, re-preview.
5. Log every task to memory: `memory.py log meshy_history '{"name":...,"task_id":...,"prompt":...,"status":...}'`
   and cost to `credits`.

## Gate
All spec'd GLBs in `~/meshy/downloads/`, each with a meshy_history entry.

## Failures
404 → API drift (OPS_LESSONS §3). 401 → key. Deformed mesh → re-prompt max 2, then
procedural fallback via router. Quota → producer briefs the Creative Director.
