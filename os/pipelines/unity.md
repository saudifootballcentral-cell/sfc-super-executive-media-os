# Pipeline — Unity (import / assemble / logic)

Stages: `unity_import`, `visual_qa`, `scene_assembly`, `gameplay_systems` … `audio`

## Import
`siraj-build.sh` copies FBX → `Assets/<Category>/` then POSTs MCP `assets_refresh`.
`SirajAssetPostprocessor.cs`: `Characters/` ⇒ Humanoid rig, `_COL_` meshes ⇒ MeshCollider,
Meshy textures extracted. Verify per asset: `[Siraj] imported ...` in `logs/unity.log`;
characters have a valid Avatar. Batch ≤5 per refresh.

## Visual QA
`SirajBridge.PreviewAsset(path)` + MCP screenshot per Meshy asset → art-director verdict.
Defect ⇒ re-prompt or retexture upstream; never hand-patch a mesh in Unity.

## Construction
Project layout: `Assets/{Characters,Models/<Game>,GameSpecs,Prefabs,Scripts/<Game>,Scenes}`.
One state machine owns the round (Setup → Countdown → Playing → RoundEnd); one mechanic =
one MonoBehaviour; input behind an interface; keyboard test input always.

## Gate chain
imports verified → visuals approved → scene playable → Playing state reached with zero
console errors.
