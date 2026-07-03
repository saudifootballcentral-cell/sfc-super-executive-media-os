# MOMENTS — Vertical Slice Technical Spec
*technical-director · task f68d72391c98*

## Platform & rendering
- Unity **6000.4.x** (matches the studio's 6000.4.8f1 editor), **URP**,
  linear color, target **60 FPS** on smart-TV-class hardware.
- Addressables for the mini-game scene so the shell stays stable as content
  scales (bible §10). Cinemachine for the arena camera + Final Duel zoom.
- No realtime lightmap bakes (studio VM law); baked-look achieved with
  gradient ambient + 1 directional + rim light material response.

## Scenes
`TV_Boot(Attract) · TV_Join · TV_Lobby · TV_Intro · TV_Play_PolarPush ·
TV_Results · TV_Finale` (+ `TV_Vote` stub for Alpha). Persistent bootstrap
scene carries the managers via additive loading.

## Core systems (class map, from GDD v1 naming — keep names)
| Class | Responsibility |
|---|---|
| SessionStateManager | Phase enum state machine; single source of truth; list-copy iteration (no ConcurrentModification) |
| PlayerRegistry | slot, nickname, heroId, ready, connection, score; 10s reconnect grace + bot takeover |
| ControllerGateway | normalizes phone/bot input; assigns UICommand layouts (`show_joystick`) |
| PhoneControllerServer | embedded HTTP server serving `phone-controller.html` (single self-contained file) |
| MomentsWebSocketServer | custom C# WebSocket server; room token auth; input intent only |
| CharacterDefinition (SO) | heroId, names AR/EN, fantasy line, portrait, prefab, color, emotes, **ability hooks (dormant in slice)** |
| CharacterAbilitySystem | passive/dash/weapon/special slots — slice: dash only, identical params (ruling 2) |
| MiniGameBase → PolarPushGame | timer, spawn, scoring, hazard scheduling contract |
| IcePlatformManager | ring-tile graph, 3-state tile lifecycle, Fisher-Yates outer-ring collapse |
| ArenaHazardSystem | telegraph standard (2s TV warning + phone haptic) → BlizzardGust force event |
| BotController | Normal AI; same input API as ControllerGateway clients; seedable |
| HUDManager / ResultsAggregator | TV HUD, standings, medals, podium data |
| VFXManager | procedural: dash trails (LineRenderer/Trail), hit sparks (expanding fade spheres), ice-crack decals, confetti |
| AudioManager | spatial SFX, procedural pitch-shift, arctic ambience loop; announcer text stub AR/EN |

## Networking
- Dual local server on the host: HTTP (controller page) + WebSocket (play).
- QR encodes `http://<host-LAN-ip>:<port>/?t=<roomToken>`.
- Phones send **intent only** (`{seq, moveX, moveY, dash}` ≤ 20 Hz);
  host validates and simulates; snapshots back with
  `lastProcessedInputSequence` for client-side prediction on the phone UI.
- Timer/score broadcast throttled (events + 1 Hz), never per-frame.
- Disconnect: transport event → PlayerRegistry grace window → bot takeover.

## Performance budgets
- Heroes ≤15k tris ea (LOD1 8k), arena ≤30k total, ≤40 draw-call budget for
  gameplay scene, zero per-frame GC allocs in Update paths (cached lists),
  pooled VFX only.

## Test plan (feeds qa_playtest gate)
1. Bots-only full round (headless CI-able).
2. 1 phone + 3 bots on LAN; input latency subjective check (<50ms target).
3. Disconnect mid-round → bot takeover → rescan reclaim.
4. 8-player lobby stress with duplicate-join and room-full paths.
5. Profiler capture on reference hardware; 60 FPS sustained incl. Final Duel.

## Risks & mitigations
- **LAN reachability on dev VM**: phones can't reach a cloud VM's localhost —
  QA on LAN hardware for the phone leg; bots cover everything else.
- **WebSocket implementation drift**: keep the protocol tiny (4 message
  types in slice) and versioned (`v` field) from day 1.
- **Style drift across Meshy heroes**: image-to-3d from key art; asset_refine
  normalizes scale/pivot; art-director visual QA gate is mandatory.
- **VM memory during import**: sequencing law; imports batched ≤5.
