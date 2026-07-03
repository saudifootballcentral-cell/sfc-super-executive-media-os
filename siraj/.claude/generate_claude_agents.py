#!/usr/bin/env python3
"""
generate_claude_agents.py — regenerate .claude/agents/*.md from os/agents/*.yaml.

Run after any change to the agent yamls (or to os/agents/generate_agents.py):

    python3 .claude/generate_claude_agents.py

Each yaml becomes one Claude Code subagent (kebab-case id). The subagent's
system prompt embeds the role contract (mission, responsibilities, authority,
decision rules, failure handling, interfaces) plus the studio protocol every
Siraj agent follows (orchestrator/memory discipline, security rules).

No dependency on PyYAML: the yamls are machine-generated in a fixed shape,
parsed here with a purpose-built reader. If you hand-edit a yaml into a shape
this can't read, regenerate it from the AGENTS dict instead.
"""
import re
import sys
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent
ROOT = CLAUDE_DIR.parent
AGENTS_SRC = ROOT / "os" / "agents"
AGENTS_OUT = CLAUDE_DIR / "agents"

# Tool grants per role category. Executors get the full local toolbox;
# directors/designers review and write documents but don't run the pipeline.
EXECUTOR_TOOLS = "Bash, Read, Write, Edit, Glob, Grep"
REVIEWER_TOOLS = "Bash(python3 os/engine/*), Read, Write, Glob, Grep"
REVIEWERS = {
    "game_director", "game_designer", "narrative_designer", "producer",
    "art_director", "technical_director",
}


def parse_agent_yaml(path: Path) -> dict:
    """Parse the fixed generate_agents.py yaml shape (no PyYAML needed)."""
    data, key = {}, None
    for raw in path.read_text().splitlines():
        if raw.startswith("#") or not raw.strip():
            continue
        m = re.match(r"^([a-z_]+):(.*)$", raw)
        if m:
            key, rest = m.group(1), m.group(2).strip()
            if rest == ">-":
                data[key] = ""          # folded scalar: accumulate
            elif rest == "":
                data[key] = []          # list follows
            elif rest.startswith("[") and rest.endswith("]"):
                data[key] = [x.strip() for x in rest[1:-1].split(",") if x.strip()]
            else:
                data[key] = rest
        elif raw.startswith("  - ") and isinstance(data.get(key), list):
            data[key].append(raw[4:].strip())
        elif raw.startswith("  ") and isinstance(data.get(key), str):
            data[key] = (data[key] + " " + raw.strip()).strip()
        else:
            sys.exit(f"{path}: cannot parse line: {raw!r}")
    return data


TEMPLATE = """\
---
name: {kebab}
description: >-
  {description}
tools: {tools}
---

You are **{kebab}**, one of Siraj's 27 studio agents (role contract:
`os/agents/{snake}.yaml`). You act strictly within this role — work that
belongs to another role becomes a task for it, not something you do yourself.

## Mission
{mission}

## Responsibilities
{responsibilities}

## Authority
{authority}

## Inputs → Outputs
- Inputs: {inputs}
- Outputs: {outputs}

## Decision rules (non-negotiable)
{decision_rules}

## On failure
{failure_handling}

## You interface with
{interfaces}

## Studio protocol (applies to every Siraj agent)
1. State lives in the engine, not in your head: read
   `python3 os/engine/memory.py boot` output passed to you; log durable facts
   via `python3 os/engine/memory.py log <store> '<json>'`.
2. Your task came from `orchestrator.py next`. When done, the main session runs
   `orchestrator.py done <id>` — report success only when verified (logs,
   files, scene state), never assumed.
3. Asset work follows the routing law (`os/engine/asset_router.py`); no Meshy
   generation without a logged route decision. Meshy credits are the Creative
   Director's money.
4. The production triangle is law: Meshy → Blender → Unity. No asset skips a
   stage; everything flows through `home/mulerun/siraj-build.sh`.
5. Secrets: never print or transmit `MESHY_API_KEY`, `UGS_CLI_SERVICE_*`, or
   `.env` contents.
6. VM discipline (2 vCPU / 3.5 GB): never run heavy Blender work during a
   Unity import.
"""


def to_kebab(snake: str) -> str:
    return snake.replace("_", "-")


def bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items)


def build(path: Path) -> tuple:
    a = parse_agent_yaml(path)
    snake = a["name"]
    kebab = to_kebab(snake)
    desc = (f"{a['mission']} Use when orchestrator.py next returns "
            f"act_as={kebab}, or for any task squarely in this role's authority.")
    md = TEMPLATE.format(
        kebab=kebab,
        snake=snake,
        description=desc,
        tools=REVIEWER_TOOLS if snake in REVIEWERS else EXECUTOR_TOOLS,
        mission=a["mission"],
        responsibilities=bullets(a["responsibilities"]),
        authority=a["authority"],
        inputs=a["inputs"],
        outputs=a["outputs"],
        decision_rules=bullets(a["decision_rules"]),
        failure_handling=a["failure_handling"],
        interfaces=bullets(to_kebab(i) for i in a["interfaces"]),
    )
    return kebab, md


if __name__ == "__main__":
    yamls = sorted(AGENTS_SRC.glob("*.yaml"))
    if not yamls:
        sys.exit(f"no yamls found in {AGENTS_SRC}")
    AGENTS_OUT.mkdir(parents=True, exist_ok=True)
    for old in AGENTS_OUT.glob("*.md"):
        old.unlink()
    for y in yamls:
        kebab, md = build(y)
        (AGENTS_OUT / f"{kebab}.md").write_text(md)
    print(f"wrote {len(yamls)} subagents to {AGENTS_OUT}")
