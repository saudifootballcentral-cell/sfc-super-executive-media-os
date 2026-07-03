# MOMENTS — Vertical Slice GDD (consolidated, rulings applied)
*game-designer · supersedes nothing — scopes the 5 source docs down to the
approved slice. Precedence for anything not covered here: master bible v2.2
→ description v2.0 → GDD v1.*

## Creative Director rulings (2026-07-03, binding)
1. **Scope**: Vertical Slice = full funnel + Polar Push + bots + reconnect.
2. **Heroes**: CharacterAbilitySystem hooks in the architecture; the slice
   runs identical stats for all heroes ("fair slice"); abilities switch on in
   Core Alpha behind a host toggle after a balance pass.
3. **Roster**: 4 heroes in the slice — Byte, Nova, Orbit, Pop. All 8 by Alpha.

## Session flow (slice)
`Attract → Join → Lobby → Intro → Polar Push → Results → Podium → Rematch/Attract`
managed by SessionStateManager (Phase enum). No vote screen in the slice
(one game); TV_Vote ships as a stub scene for Alpha.

- **Attract**: logo, animated background, large QR + room code, hero idle loop.
- **Join**: phone opens web controller with embedded room token → nickname →
  hero carousel (portrait, name, one-line fantasy; taken heroes marked) →
  tap select, hold to lock → Ready. TV player cards update live.
- **Intro**: bilingual rules card (AR/EN) 8s + phone swaps to joystick+dash
  layout with haptic confirm.
- **Results**: standings + medals; **Podium** after final round: winner
  choreography, confetti. Rematch returns to Lobby with roster kept.
- **Reconnect**: 10s grace; slot+hero+score reserved; bot takes over after
  grace, player can reclaim on rescan.

## Polar Push (slice content)
- **Objective**: last hero standing on a shrinking ice platform. 2–8
  players/bots, round cap 120s. Win = survival; podium points by placement.
- **Platform**: circular tile arena (IcePlatformManager). Tiles have 3
  readable states — solid → cracked → breaking — then drop. Fisher-Yates
  randomized outer-ring collapse over time.
- **Movement**: slippery acceleration (ice friction), push on contact
  (body mass + velocity), universal **Dash** (same numbers for every hero,
  hero-colored trail VFX), 1.5s cooldown shown on the phone button.
- **Hazard**: **Blizzard Gust** — 2s telegraph (TV warning + 3 short phone
  vibrations, per the telegraph standard) then a strong directional wind
  force for 3s.
- **Final Duel**: at 2 players left, camera zooms, slow-mo sting, arena
  shrinks to the center ring.
- **Deferred to Alpha** (explicitly out of slice): grab & throw, power-up
  crates, arena variants (Glacier Ring / Iceberg Tilt / Frozen Lake), Orca
  Breach + Freezing Fog hazards.

## Heroes (slice)
| Hero | Fantasy | Color | Signature read |
|---|---|---|---|
| Byte | Arcade tech kid | Neon blue #00BFFF | Black hoodie, LED smiley visor, headset |
| Nova | Star hunter | Star gold/magenta | Pink ponytail, star goggles, badge jacket |
| Orbit | Mini astronaut bot | Toxic green on black | Round black visor, green glow eyes, suit |
| Pop | Chaos maker | Neon pink #FF3399 | Blue hair, smiley cap, bubblegum |
Identical stats in the slice (ruling 2). Each hero: portrait, 3D prefab
(15k tris, shared Mecanim rig), 11-clip shared animation set, colored dash
trail, podium pose. CharacterDefinition ScriptableObject per hero.

## Phone controller (slice)
Layouts: `join/nickname/select/ready` + `show_joystick` (move stick + DASH
button + cooldown ring). Haptics: join confirm, ready confirm, hazard
warning (3 short), elimination (long), podium. Dark battery-safe play
screen framed in player color. Spectator minimap after elimination.

## Bots
Fill to minimum 4 participants. Same input API as phones. Three levels;
slice default "Normal": seek center, avoid cracked tiles, opportunistic
push, dash on target lined up. Deterministic seed option for QA.

## Non-goals (slice)
Teams, tournament, mutators, power-ups, Mastery/Party Pass, shop, cloud
save, announcer VO (text stub only), 8-hero roster, other 11 mini-games.

## Acceptance (maps to stage gates 12–21)
Full round start-to-finish with 0 phones (bots), with 1 phone + 3 bots, and
with a mid-round disconnect+reconnect; win condition fires; zero
errors/warnings; 60 FPS on reference hardware; bilingual intro card.
