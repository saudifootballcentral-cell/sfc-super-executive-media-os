# Moments — Unity Machine Runbook (stages 10 → 21)

Everything before stage 10 is done and committed. This runbook takes the
Unity machine from clone to first playable build. Each step names the
orchestrator gate it provides evidence for.

## 0. Prerequisites (once)
- Unity 6 (6000.x) with URP; licensed (`home/mulerun/unity_cloud/unity_license.sh check`)
- This repo cloned; `./siraj-activate.sh check` green on the engine self-tests
- `MESHY_API_KEY` in `home/mulerun/.env` (only needed for new generations)

## 1. Project drop-in
Copy `projects/moments/unity/Assets/.` into your Unity project's `Assets/`
(or open a new URP project and drop it in). Contents:
- `Assets/Characters/` — 8 rigged heroes + HeroAnimationSet (auto-Humanoid via postprocessor)
- `Assets/Models/Moments/` — arena set (auto MeshCollider on `_COL_`)
- `Assets/_Moments/` — all 15 C# systems
- `Assets/Editor/` — SirajBridge, SirajAssetPostprocessor, **MomentsSetup**
- `Assets/StreamingAssets/phone-controller.html`

Let Unity import (batch ≤5 if it struggles; watch for `[Siraj] imported ...`).

## 2. Stage 10 — unity_import
Run **Siraj → Moments → 1 Verify Imports**. Console must show
`15 ok, 0 bad`. Then:
```bash
python3 os/engine/orchestrator.py task '{"stage":"unity_import","title":"Verify 15 imports + avatars"}'
python3 os/engine/orchestrator.py next   # take the task id
python3 os/engine/orchestrator.py done <id>
python3 os/engine/orchestrator.py gate unity_import pass "MomentsSetup verify: 15 ok, avatars valid"
```

## 3. Stage 11 — visual_qa
For each hero: `SirajBridge.PreviewAsset("Assets/Characters/<Hero>.fbx")`,
screenshot, compare against `projects/moments/concept/refs/` pairs.
Creative Director approves → gate pass. (Renders from the cloud QA already
exist in `projects/moments/meshy/` as the baseline.)

## 4. Stage 12 — scene_assembly
Run **Siraj → Moments → 2 Create Character Definitions**, then
**3 Build Boot Scene**, then **4 Build PolarPush Scene**.
Gate evidence: both scenes exist, in build settings, arena has colliders.

## 5. Stage 13 — gameplay_systems
Open TV_Play_PolarPush, add a bootstrap that calls `PolarPushGame.Begin()`
on Play (or call it from the inspector). Bots fill to 4 and the round runs.
Gate: reaches Playing with zero console errors.

## 6. Stages 14–17 — ai_systems · ui_ux · vfx_polish · audio
- ai_systems: BotController already drives bots; tune difficulty; gate.
- ui_ux: wire HUDManager bindings (timer text, cards); phone flow live test.
- vfx_polish: VFXManager procedural effects (GDD §6: LineRenderer arcs,
  trail dashes, expanding hit spheres) wired to events + telegraph banner.
- audio: arctic ambience loop + event SFX map, -6dB ceiling.

## 7. Stage 18 — qa_playtest (TECH_SPEC test plan)
1. Bots-only full round — win fires.
2. Phone on LAN: QR from `PhoneControllerServer.JoinUrl()` (log prints it),
   join → nickname → hero → ready → play with joystick+dash.
3. Mid-round disconnect → 10s grace → bot takeover → rescan reclaim.
4. Zero errors, zero warnings. Log bugs via `memory.py log bugs`.

## 8. Stage 19 — optimization
Profiler on target hardware; 60fps sustained incl. Final Duel slow-mo.
Order if under: particles → decimate → shaders → count.

## 9. Stages 20–21 — build · publishing
```
Unity -batchmode -nographics -quit -projectPath <proj> \
      -buildTarget <target> -executeMethod <BuildScript>
```
Artifact launches to attract screen → gate build.
Delivery: artifact + this repo's docs + credits report → Creative Director
sign-off → gate publishing. **21/21.**

## If anything fails
`os/OPS_LESSONS.md` first (lockfiles, OOM, API drift), then the self-repair
loop: `orchestrator.py fail <id> "<root cause>"` — 3 strikes escalate.
