# سراج (Siraj) — Enterprise Game Development OS

> **Canonical home**: this tree is designed to live as the root of the
> dedicated `Siraj` repository (see `MIGRATION.md`). Engine state and all
> game objects are tracked in git — only secrets are not.

An autonomous game-development agent that runs as a **Claude Code project**:
one brain, 27 specialist studio agents, a file-based orchestration engine,
and a real **Meshy → Blender → Unity** production pipeline. Idea in,
playable Unity build out.

```
CLAUDE.md                 project constitution (auto-loaded every session)
.claude/agents/           27 subagents — generated, do not edit by hand
.claude/skills/           /siraj-boot ·new ·dispatch ·run ·route ·gate ·status
.claude/hooks/            guard-secrets.sh — blocks secret-leaking Bash calls
.mcp.json                 siraj-unity bridge (127.0.0.1:8080)
os/engine/                orchestrator.py · asset_router.py · memory.py
os/agents/                27 role contracts (*.yaml) + generate_agents.py
os/pipelines/             meshy · blender · unity · qa · self_repair · build · publishing
os/ARCHITECTURE.md        ADR-001..003, layer model, the 21 stages
os/OPS_LESSONS.md         hard-won server lessons — read before diagnosing
os/ROADMAP.md             7 phases (1–4 shipped)
os/runtime/               live queue + gates (engine-owned, git-ignored)
memory/                   9 persistent stores (engine-owned, git-ignored)
home/mulerun/             execution layer: meshy client, Blender refine,
                          siraj-build.sh, Unity editor bridge, Unity Cloud tools
workspace/                Siraj's identity + operating doctrine
siraj-activate.sh         one-command install + readiness check + self-test
```

## Install

Server install (Unity 6 + Blender 4.4 + MCP bridge): `INSTALL.md`.
Claude Code setup and first run: `INSTALL_CLAUDE_CODE.md` (Arabic).
Quick check on any machine: `./siraj-activate.sh check` — the engine
self-tests (compile, router law, memory, orchestrator) must all pass ✅.

## How it runs

```
/siraj-boot                      # read real state from the engine
/siraj-new <game idea>           # game-director drafts the plan → your approval
/siraj-dispatch                  # one supervised production cycle
/siraj-run 10                    # ten autonomous cycles
```

Every cycle: `orchestrator.py next` names the task and the owning agent →
the brain invokes that agent via the Task tool → `done`/`fail` → gates pass
strictly in order through the 21 stages. Skipping a stage is mechanically
impossible; three failures on one task escalate to you, the Creative
Director.

## The laws

1. **The triangle**: design → Meshy (generate) → Blender (repair/decimate/rig)
   → Unity (produce). No asset skips a stage; everything flows through
   `siraj-build.sh`.
2. **The routing law**: reuse → retexture → procedural → meshy → marketplace
   → manual. No Meshy spend without a logged route decision — credits are
   the Creative Director's money.
3. **Memory law**: `memory.py` is the sole writer of `memory/*.json`;
   `orchestrator.py` is the sole writer of `os/runtime/`. Never edit these
   by hand.
4. **Secrets law**: `MESHY_API_KEY` and Unity service credentials live in
   `home/mulerun/.env` (chmod 600) only — the PreToolUse guard blocks
   commands that would print or exfiltrate them.

## Regenerating agents

```bash
python3 os/agents/generate_agents.py        # AGENTS dict → os/agents/*.yaml
python3 .claude/generate_claude_agents.py   # yamls → .claude/agents/*.md
```
