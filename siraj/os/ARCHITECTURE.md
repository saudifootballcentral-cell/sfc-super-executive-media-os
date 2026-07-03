# Siraj OS — Architecture

Siraj is an Enterprise Autonomous Game Development Platform running as a
Claude Code project. One brain (the main session), 27 specialist roles,
one file-based engine, one real production pipeline.

## Layer model

```
┌─ Interface ────────────────────────────────────────────────────────┐
│ Claude Code session (the brain) · /siraj-* skills · CLAUDE.md      │
├─ Roles ────────────────────────────────────────────────────────────┤
│ .claude/agents/*.md  ← generated from → os/agents/*.yaml           │
│ 27 studio roles invoked via the Task tool (subagent_type=act_as)   │
├─ Engine (source of truth) ─────────────────────────────────────────┤
│ os/engine/orchestrator.py  21 stages · queue · gates · self-repair │
│ os/engine/asset_router.py  routing law (reuse→…→manual)            │
│ os/engine/memory.py        sole writer of memory/*.json            │
├─ Execution ────────────────────────────────────────────────────────┤
│ home/mulerun/: meshy_client.py · blender/scripts/meshy_refine.py   │
│ siraj-build.sh · SirajBridge.cs · SirajAssetPostprocessor.cs       │
│ unity_cloud/: license · UGS · VCS · cloud-build hooks              │
├─ Substrate ────────────────────────────────────────────────────────┤
│ Unity 6 (Xvfb :99, MCP :8080) · Blender 4.4 headless · Meshy API   │
│ VM: 2 vCPU / 3.5 GB — sequencing discipline is architectural       │
└────────────────────────────────────────────────────────────────────┘
```

## ADR-001 — Agents are roles, not processes

**Decision.** An "agent" is a role contract (mission, responsibilities,
authority, decision rules, failure handling, interfaces) executed by a
Claude Code subagent for the duration of one task. There are no daemons,
no message buses, no per-agent state.

**Why.** On a 3.5 GB VM, 27 resident processes are impossible and
unnecessary. Role contracts give the same separation of concerns at zero
runtime cost, and the Task tool already provides isolation, tool scoping
and a return channel.

**Consequences.** Concurrency is limited to what the brain deliberately
parallelizes (e.g. Meshy polling while writing C#). All coordination happens
through the engine's files, never agent-to-agent.

## ADR-002 — File-based state, one writer per file

**Decision.** All durable state is JSON on disk:
`os/runtime/` (project, queue, gates — written only by orchestrator.py) and
`memory/` (nine stores — written only by memory.py). Every write is
atomic (tmp + rename).

**Why.** Files survive session death, are greppable/diffable, need no
daemon, and make the "read state at boot, never assume" rule enforceable.
A single writer per file eliminates lock contention without locks.

**Consequences.** Hand-editing queue/gate JSON is forbidden (the gate
refusal you're trying to bypass is the system working). External tools
(post-build hooks, activation script) report through `memory.py log`.

## ADR-003 — Gates are mechanical, not advisory

`orchestrator.py` will not dispatch work for a stage that isn't current and
will not pass a gate while the stage has open tasks; gates pass strictly in
order. Skipping a stage is therefore impossible by construction, matching
the constitution in `CLAUDE.md` ("no stage may be skipped").

## The 21 stages

`orchestrator.py stages` prints the machine truth. Summary:

| # | Stage | Owner (act_as) |
|---|-------|----------------|
| 1 | game_idea | game-director |
| 2 | gdd | game-designer |
| 3 | tech_spec | technical-director |
| 4 | spec_json | game-designer |
| 5 | asset_routing | asset-director |
| 6 | meshy_generation | concept-artist |
| 7 | procedural_assets | environment-artist |
| 8 | asset_refine | asset-director |
| 9 | rigging_animation | rigging-engineer |
| 10 | unity_import | unity-architect |
| 11 | visual_qa | art-director |
| 12 | scene_assembly | level-designer |
| 13 | gameplay_systems | gameplay-programmer |
| 14 | ai_systems | ai-programmer |
| 15 | ui_ux | ui-ux-director |
| 16 | vfx_polish | vfx-director |
| 17 | audio | audio-director |
| 18 | qa_playtest | qa-director |
| 19 | optimization | optimization-director |
| 20 | build | build-engineer |
| 21 | publishing | producer |

The 9 phases of `workspace/SIRAJ_OS.md` §4 map onto these 21 stages
(Phase 1 → stages 1–3, Phase 2 → 4–5, Phase 3 → 6–7, Phase 4 → 8–9,
Phase 5 → 10–11, Phase 6 → 12–17, Phase 7 → 18–19, Phase 8 → 20,
Phase 9 → 21).

## Self-repair loop

`fail <id>` re-queues a task with an attempt counter. Three failures move it
to `queue/failed/` with `escalated: true` and log a decision entry —
technical-director then briefs the Creative Director with at least two
options. Details: `os/pipelines/self_repair.md`.

## Regeneration chain

```
os/agents/generate_agents.py (AGENTS dict — edit here)
        │ python3 os/agents/generate_agents.py
        ▼
os/agents/*.yaml (role contracts, machine-readable)
        │ python3 .claude/generate_claude_agents.py
        ▼
.claude/agents/*.md (Claude Code subagents — never edit by hand)
```
