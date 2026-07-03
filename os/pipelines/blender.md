# Pipeline — Blender (repair / procedural / rig)

Stages: `procedural_assets`, `asset_refine`, `rigging_animation`

## Refine (every Meshy asset)
`siraj-build.sh --meshy <glb> <Name> <Category> [--rig]` runs
`blender --factory-startup -b -P scripts/meshy_refine.py` which: joins meshes,
grounds the pivot, decimates to budget (Characters 15k / Props 8k / Arenas 30k),
optional simplified Mecanim rig, exports FBX (-Z forward / Y up, scale 1, no leaf bones).

## Procedural
`siraj-build.sh tasks/<script>.py <Name> <Category>` — Dhai factories
(arena/character/weapon/animation). Exact dims from spec; collider meshes named `_COL_`.

## Rules
- Wrong FBX scale is fixed HERE (global_scale in meshy_refine.py), never per-asset in Unity.
- Mecanim bone names only: Hips/Spine/Chest/Neck/Head/Left|Right(UpperArm…).
- VM law: no heavy Blender during a Unity import.

## Gate
`~/blender/exports/<Name>.fbx` exists for every spec asset.
