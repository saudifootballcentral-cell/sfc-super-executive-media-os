# OPS_LESSONS — what actually happened on the server

Operational lessons inherited from Dhai's real sessions on the shared VM.
Read this before diagnosing any Unity/MCP/Blender problem — most "new"
failures below have already been solved once.

## §1 Unity headless boot

- **Zero-byte lockfiles kill Unity silently.** After a crash, `UnityLockfile`
  or `*.lock` files of size 0 remain and Unity exits without a useful error.
  `siraj-activate.sh` deletes them automatically; if Unity won't boot, check
  for them first: `find ~/unity6 -name '*.lock' -o -name UnityLockfile`.
- Unity needs Xvfb `:99` even in batch mode for some import paths. If
  `pgrep -f "Xvfb.*:99"` is empty, `start-dhai.sh` brings it up.
- License is machine-bound (.alf → license.unity3d.com/manual → .ulf).
  Rebuilding the VM invalidates it — plan the manual browser step with the
  owner before any rebuild. `unity_license.sh check` tells you where you are.

## §2 Memory (the 3.5 GB kind)

- Unity import + heavy Blender simultaneously = OOM killer picks one, you
  lose both. The sequencing law (Meshy poll ∥ write C# → Blender → Unity
  import) exists because we paid for it.
- Unity OOM during import: `DHAI_NOGFX=1 start-dhai.sh restart`, then retry
  the refresh. Batch imports in groups of ≤5 — domain reloads compound.

## §3 Meshy API drift

- Meshy has moved endpoints between versions before (v1 → v2 text-to-3d).
  A sudden 404 on a previously working call means the API moved, not that
  your key died (that's a 401). Check docs.meshy.ai, update the paths in
  `meshy_client.py`, nothing else.
- Preview is cheap, refine is not. A wrong silhouette discovered after
  refine is money burned twice.

## §4 Unity VCS (Plastic/cm) — syncing a real project from Unity Cloud

The proven path (Dhai's Moments repo, org 18968407097579):

- `unity_vcs.sh setup <ORG_ID>` installs and configures `cm` against
  `<ORG_ID>@unity`.
- **First `repos` call opens a browser login with the Unity ID.** On a
  headless server do this once through VNC; the session token persists
  afterwards and everything else is automatable.
- `clone` into the Unity project directory, then `update` runs in the
  background — watch `/tmp/cm_update.log`, not the terminal, for progress.
- What failed: trying to script the browser auth (don't — it's one-time),
  and running `update` while Unity had the project open (close Unity or
  expect file locks).
- What worked: clone → update → open Unity → let it reimport, in that order.

## §5 The MCP bridge is REST until proven otherwise

- The bridge on 127.0.0.1:8080 historically speaks plain REST
  (`POST /tools/assets_refresh`), not MCP JSON-RPC. `.mcp.json` is provided
  for when it grows a real `/mcp` endpoint; if `claude mcp list` shows
  `siraj-unity` failed, that's cosmetic — every agent has Bash and
  `siraj-build.sh`/`curl` do the same job. Do not sink time into "fixing"
  the connection before checking which protocol the bridge actually speaks:
  `curl -s http://127.0.0.1:8080/ | head`.
- MCP unreachable during a build: `start-dhai.sh status`/`restart`. If still
  down, halt and report — blind file drops into Assets/ without a refresh
  create half-imported states that cost more to clean than the wait.

## §6 Engine discipline

- The gate refusal ("open tasks in stage") is not a bug. Finish or fail the
  tasks. Editing `os/runtime/` JSON by hand has corrupted a queue before —
  that's why memory.py/orchestrator.py are the only writers.
- `memory.py boot` failing at session start blocks everything: diagnose the
  corrupt store it names (a truncated write from a killed session is the
  usual cause), restore from the `.tmp` neighbor if present.
