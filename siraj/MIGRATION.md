# Making this repository Siraj's home

This tree IS the complete Siraj production state — engine, 27 agents,
skills, security guard, the Moments project at 9/21 gates, all game
objects (8 rigged heroes, 6 arena pieces, 11-clip animation set, GLBs,
renders, reference art) and the full memory/decision trail.

## Seed (one time, from any machine with git)
```bash
git clone -b siraj-standalone https://github.com/saudifootballcentral-cell/sfc-super-executive-media-os siraj-seed
cd siraj-seed
git push https://github.com/saudifootballcentral-cell/Siraj.git siraj-standalone:main
```
(Or in a Claude Code session scoped to the Siraj repo: paste the three
lines above as the instruction.)

## After seeding — this repo is the source of truth
- Start every Claude Code session FROM this repo; `/siraj-boot` first.
- Engine state (memory/*.json, os/runtime/) is deliberately TRACKED here:
  committing state is how production transfers between the cloud brain
  and the Unity machine. Only secrets stay out of git (.gitignore).
- The Unity machine: clone this repo, `./siraj-activate.sh check`, put
  MESHY_API_KEY in home/mulerun/.env, then
  `python3 os/engine/orchestrator.py status` resumes at stage 10.
- The old location (sfc-super-executive-media-os/siraj) is frozen
  history; do not develop there after seeding.
