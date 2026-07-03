# سراج — Systems Status & Infrastructure (v1)

## The Triangle

```
  Meshy (cloud AI gen)          Blender 4.4 (headless refine/rig/procedural)
        \  GLB                        /  FBX (-Z/Y, scale 1, no leaf bones)
         \                           /
          -->  siraj-build.sh  -----+--> Unity 6 Assets/ --> MCP assets_refresh
                                          SirajAssetPostprocessor:
                                          Characters/ => Humanoid, _COL_ => MeshCollider
```

## Meshy

| Item | Value |
|------|-------|
| Client | `/home/mulerun/meshy/meshy_client.py` |
| Auth | `MESHY_API_KEY` in `/home/mulerun/.env` |
| Endpoints | v2 text-to-3d (preview/refine), v1 image-to-3d, v1 retexture |
| Downloads | `/home/mulerun/meshy/downloads/*.glb` |
| Note | Verify endpoint versions against docs.meshy.ai if a call 404s |

## Blender

| Item | Value |
|------|-------|
| Binary | `/home/mulerun/blender/blender` (headless, `--factory-startup`) |
| Meshy refine | `scripts/meshy_refine.py` — join, ground pivot, decimate, optional Mecanim rig, FBX export |
| Procedural | reuse Dhai factories: `blender_pipeline.py`, `arena_factory.py`, `character_factory.py`, `weapon_factory.py`, `animation_library.py` |

## Unity 6

| Item | Value |
|------|-------|
| Version | 6000.4.8f1 — Xvfb :99, MCP on 127.0.0.1:8080 (localhost only) |
| Editor bridge | `Assets/Editor/SirajBridge.cs` + `SirajAssetPostprocessor.cs` |
| Poly budgets | Characters 15k / Props 8k / Arenas 30k |

## Constraints (VM = 2 vCPU / 3.5 GB RAM)

- Sequence heavy work: Meshy poll (cheap) || write C# — then Blender — then Unity import. Never Blender-heavy + Unity-import simultaneously.
- If Unity OOMs: `start-dhai.sh restart` (shared services) with `DHAI_NOGFX=1`.

## Active Projects

(append status per game here — this file is Siraj's working memory)

### Moments — Vertical Slice (active)
- Gates: 8/21 passed; stage 9 (rigging_animation) — rigs done, 11-clip animation set pending
- Roster: 7/8 heroes CANON (official-art image-to-3d, rigged, 15k, Unity FBX in projects/moments/exports/) — Nova awaits her reference sheet
- Arena: 6 procedural FBX (tiles x3, rim+_COL_, icebergs x2)
- Code: 15 C# systems + phone-controller.html prebuilt for stage 13
- Credits: ~360 spent, 1190 remain (floor alarm 100)
- Blocked: Unity stages (10+) need the machine with Unity 6; repo write access 403 (12+ commits local, snapshots delivered to owner)

