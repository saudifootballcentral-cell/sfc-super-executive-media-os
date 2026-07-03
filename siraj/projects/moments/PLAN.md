# MOMENTS — Phase-1 Development Plan
*game-director · task 4ffd73e14bc2 · stage game_idea · awaiting Creative Director approval*

## 1. What we are building

Moments: a TV-as-server local-multiplayer party game. The TV (Unity 6 + URP)
hosts the authoritative session; 2–8 players join in seconds by scanning a QR
code that opens a web controller on their phone (no app, no pairing). Heroes,
mini-games, hazards, power-ups and mutators are all data-driven
(ScriptableObjects). Target: stable 60 FPS on smart-TV-class hardware,
bilingual (Arabic/English) presentation.

Sources of truth, in order of precedence:
1. `gdd/master_design_bible_v2_2.txt` (self-declared main reference)
2. `gdd/game_description_v2.txt` (12-mini-game "Complete Feature Edition")
3. `gdd/gdd_v1_full.txt` + `game_description_v1.txt` (systems detail: class names, networking)
4. `gdd/character_design_pack_v1_2.txt` (roster production spec)
5. `concept/` — 7 key-art pieces + 1 gameplay video (visual style law)

## 2. Recommended milestone: VERTICAL SLICE

Per the bible's own roadmap. Proves the entire promise end-to-end:

```
TV attract (QR) → phone join → nickname → hero select → ready
→ Polar Push (fully polished) → results → podium → rematch
+ reconnect grace + AI bots filling empty slots
```

**Why Polar Push first:** the bible names it first; simplest controller
(move + dash) proves the input pipeline; survival objective is readable at a
glance; we already hold finished bilingual key art for it.

## 3. Asset plan (routes per the routing law)

| Asset | Route | Notes |
|---|---|---|
| 4 heroes: Byte, Nova, Orbit, Pop | meshy image-to-3d from key art + Blender rig | 15k tris, shared Mecanim rig, LOD1; the 4 with strongest concept coverage |
| 4 heroes: Striker, Sizzle, Shade, Dusty | deferred to Core Alpha | text-to-3d with locked style prompt |
| Ice arena tiles (3 damage states) | procedural (Blender) | exact dims, `_COL_` colliders; IcePlatformManager drives them |
| Arena dressing (icebergs, penguin, flags) | procedural | under-a-minute geometry |
| Power-up crates | procedural | shared across all mini-games |
| Hero animation set (11 clips) | Blender animation_library on shared rig | idle/ready/celebrate/lose/point/laugh/clap/shocked/dance/intro/podium |
| VFX (dash trail, hit spark, ice crack, confetti) | Unity procedural (VFXManager per GDD) | no Meshy, no heavy particle prefabs |

**Credits estimate:** slice ≈ 4 image-to-3d generations (+2 re-prompt
reserve); alpha adds ≈ 4 text-to-3d + tank retextures ≈ 8–12 more.
Awaiting the actual Meshy plan/credit budget from the Creative Director.

## 4. Systems plan (vertical slice)

- **SessionStateManager** — the five-phase state machine (Attract → Lobby →
  Load → Action → Results); single source of truth.
- **ControllerGateway** — HTTP server (`phone-controller.html`) + custom C#
  WebSocket server; client-side prediction (inputSequence /
  StateSnapshotMsg); 10s disconnect grace with slot reservation.
- **PlayerRegistry, CharacterDefinition SOs** — roster data-driven from day 1.
- **MiniGameBase → PolarPush** — IcePlatformManager (Fisher-Yates tile
  collapse, 3 crack stages), Blizzard Gust hazard via ArenaHazardSystem,
  Final Duel camera moment.
- **AI bots** — 3 difficulty levels through the same input API as phones
  (the local-first law: full round playable with zero phones).
- **HUDManager, ResultsAggregator, podium scene**, dynamic camera (basic),
  bilingual announcer stub (AR/EN lines wired, full VO later).
- **Phone UI** — join → nickname → hero carousel → ready → joystick+dash
  layout; player-color framing; haptic grammar v1.

## 5. Design ruling required (contradiction in the GDD set)

The bible (v2.2) says characters are **cosmetic-first**; GDD v1 and the v2
description give heroes **unique stats + abilities** (CharacterAbilitySystem).

**Recommendation:** build the CharacterAbilitySystem hooks into the
architecture now, but ship the vertical slice with identical stats
(cosmetic-first) — proving the funnel with fair heroes — then switch
abilities on in Core Alpha behind a host toggle after a balance pass.
Either final ruling costs nothing extra this way.

## 6. Milestones

| Milestone | Contents | Stage span |
|---|---|---|
| **Vertical Slice** | funnel + Polar Push + bots + reconnect | 1–21 (this run) |
| Core Alpha | +Color Clash, Tank Battle, Bumper Blitz; 8 heroes; abilities toggle; mutators | new cycle |
| Content Beta | 7 games, audio pass, Mastery XP, accessibility, AR/EN VO | new cycle |
| v2.0 | 12 games, teams/tournament, Party Pass, share cards | new cycle |

## 7. Risks

1. **Design contradiction** (§5) — needs the ruling above.
2. **Phone reachability**: WebSocket serving requires the host and phones on
   one LAN; dev VM is headless/cloud — bots + a local test client cover QA
   until a real living-room test.
3. **Meshy style drift** vs the key art — image-to-3d from the art itself +
   locked style prompt suffix + retexture-not-regenerate for fixes.
4. **VM limits (2 vCPU/3.5GB)**: 8 avatars + arena in lobby → enforce LODs,
   sequencing law during imports.
5. **Environment split**: stages 1–5 run in this cloud session; stages 6–21
   (Meshy/Blender/Unity) require the game server. State transfers via git —
   on the server: `git pull`, then `orchestrator.py status` resumes exactly
   here.

## 8. Approval requested (gate: game_idea)

1. Approve Vertical Slice scope (funnel + Polar Push + bots)?
2. Ruling on §5: cosmetic-first slice with ability hooks — approved?
3. Roster: 4 heroes in the slice (Byte, Nova, Orbit, Pop), 8 by Alpha?
4. Meshy account plan + monthly credit budget?
