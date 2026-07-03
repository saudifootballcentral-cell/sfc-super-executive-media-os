#!/usr/bin/env python3
"""
orchestrator.py — Siraj's production orchestrator.

21-stage lifecycle, file-based task queue, mechanical gate enforcement
(skipping a stage is impossible: `next` only dispatches tasks for the
current stage, and a gate refuses to pass while the stage has open tasks),
and a self-repair loop (a task may fail MAX_ATTEMPTS times before it is
escalated to the Creative Director via technical-director).

State lives under os/runtime/:
  project.json            the active project
  queue/{inbox,active,done,failed}/<task-id>.json
  gates/<stage>.json      gate verdicts (also mirrored to memory 'gates')

Usage:
  python3 orchestrator.py new "<Game Name>" [--force]
  python3 orchestrator.py task '{"stage":"game_idea","title":"...","priority":9}'
  python3 orchestrator.py next            # -> current task + act_as agent
  python3 orchestrator.py done <task-id>
  python3 orchestrator.py fail <task-id> [reason]
  python3 orchestrator.py gate <stage> pass|fail [note]
  python3 orchestrator.py status
  python3 orchestrator.py stages
"""
import json
import re
import sys
import time
import uuid
from pathlib import Path

import memory  # sibling module — sole writer of memory/*.json

OS_DIR = Path(__file__).resolve().parent.parent
RUNTIME = OS_DIR / "runtime"
QUEUE = RUNTIME / "queue"
GATES = RUNTIME / "gates"
PROJECT_FILE = RUNTIME / "project.json"

MAX_ATTEMPTS = 3  # self-repair cycles before escalation

# The 21 stages. Order is law — see os/ARCHITECTURE.md and CLAUDE.md.
# act_as = default owning agent (kebab-case, matches .claude/agents/<id>.md
# and os/agents/<id_snake>.yaml).
STAGES = [
    ("game_idea",        "game-director",        "Idea analyzed; development plan approved by Creative Director"),
    ("gdd",              "game-designer",        "GDD written and internally consistent"),
    ("tech_spec",        "technical-director",   "Technical spec: systems, risks, platform targets"),
    ("spec_json",        "game-designer",        "Assets/GameSpecs/<Game>.json complete — every asset has route + poly budget"),
    ("asset_routing",    "asset-director",       "Every asset routed via asset_router.py; decisions logged"),
    ("meshy_generation", "concept-artist",       "All Meshy GLBs downloaded (preview approved before refine)"),
    ("procedural_assets","environment-artist",   "All procedural assets exported from Blender"),
    ("asset_refine",     "asset-director",       "Every asset through Blender refine: pivot, decimate to budget, FBX"),
    ("rigging_animation","rigging-engineer",     "Characters rigged (Mecanim names) + animation set retargets"),
    ("unity_import",     "unity-architect",      "'[Siraj] imported' per asset; Humanoid avatars valid; textures extracted"),
    ("visual_qa",        "art-director",         "Every Meshy asset previewed + screenshot approved"),
    ("scene_assembly",   "level-designer",       "Scene: lighting, camera per spec, colliders, players, UI shell"),
    ("gameplay_systems", "gameplay-programmer",  "Core loop state machine reaches Playing in Play Mode, zero errors"),
    ("ai_systems",       "ai-programmer",        "Bots/AI behaviors pass their test scene (skip-gate allowed if GDD has none)"),
    ("ui_ux",            "ui-ux-director",       "Menus, HUD, round flow UI wired to game state"),
    ("vfx_polish",       "vfx-director",         "Game feel pass: shake/hit-stop/particles on every significant event"),
    ("audio",            "audio-director",       "SFX + music wired to events; mixer levels sane"),
    ("qa_playtest",      "qa-director",          "Full round start-to-finish; win condition fires; zero warnings"),
    ("optimization",     "optimization-director","60fps on reference machine; budgets enforced"),
    ("build",            "build-engineer",       "Batch-mode build produced; launches to main menu"),
    ("publishing",       "producer",             "Delivery: build artifact + README + docs; Creative Director sign-off"),
]
STAGE_IDS = [s[0] for s in STAGES]
STAGE_OWNER = {s[0]: s[1] for s in STAGES}
STAGE_GATE = {s[0]: s[2] for s in STAGES}


def _ensure_dirs():
    for q in ("inbox", "active", "done", "failed"):
        (QUEUE / q).mkdir(parents=True, exist_ok=True)
    GATES.mkdir(parents=True, exist_ok=True)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_project():
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text())
    return None


def _save_project(project):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n")


def _tasks(queue_name):
    d = QUEUE / queue_name
    tasks = []
    if d.is_dir():
        for f in sorted(d.glob("*.json")):
            try:
                tasks.append(json.loads(f.read_text()))
            except json.JSONDecodeError:
                print(f"WARN: skipping corrupt task file {f}", file=sys.stderr)
    return tasks


def _task_path(queue_name, task_id):
    return QUEUE / queue_name / f"{task_id}.json"


def _find_task(task_id):
    for q in ("inbox", "active", "done", "failed"):
        p = _task_path(q, task_id)
        if p.exists():
            return q, p
    return None, None


def _write_task(queue_name, task):
    _ensure_dirs()
    _task_path(queue_name, task["id"]).write_text(
        json.dumps(task, ensure_ascii=False, indent=2) + "\n")


def _gate_state(stage):
    p = GATES / f"{stage}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def _gate_passed(stage):
    st = _gate_state(stage)
    return bool(st and st.get("status") == "pass")


def current_stage():
    """First stage whose gate has not passed."""
    for stage in STAGE_IDS:
        if not _gate_passed(stage):
            return stage
    return None  # all gates passed — project complete


def _open_tasks_for_stage(stage):
    return [t for q in ("inbox", "active") for t in _tasks(q) if t.get("stage") == stage]


# ---------------------------------------------------------------- commands

def cmd_new(args):
    force = "--force" in args
    names = [a for a in args if a != "--force"]
    if not names:
        sys.exit('usage: orchestrator.py new "<Game Name>" [--force]')
    existing = _load_project()
    if existing and existing.get("status") == "active" and not force:
        sys.exit(f"active project '{existing['name']}' exists — finish it or use --force")
    name = names[0]
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower() or "game"
    project = {"name": name, "slug": slug, "created": _now(), "status": "active"}
    _ensure_dirs()
    # a new project resets gates and the queue (previous project must be archived first)
    if force:
        for f in GATES.glob("*.json"):
            f.unlink()
        for q in ("inbox", "active"):
            for f in (QUEUE / q).glob("*.json"):
                f.unlink()
    _save_project(project)
    memory.append("versions", {"event": "project_new", "project": name})
    memory.append("decisions", {"kind": "project_start", "project": name,
                                "note": "lifecycle begins at stage game_idea"})
    print(json.dumps({"ok": True, "project": project,
                      "next": "create the first task: orchestrator.py task "
                              '\'{"stage":"game_idea","title":"Analyze the idea","priority":9}\''},
                     ensure_ascii=False, indent=2))


def cmd_task(args):
    if not args:
        sys.exit("usage: orchestrator.py task '<json>'")
    try:
        spec = json.loads(args[0])
    except json.JSONDecodeError as e:
        sys.exit(f"invalid JSON: {e}")
    stage = spec.get("stage")
    if stage not in STAGE_IDS:
        sys.exit(f"invalid stage '{stage}' — valid: {', '.join(STAGE_IDS)}")
    if _gate_passed(stage):
        sys.exit(f"stage '{stage}' gate already passed — new work there means the "
                 f"gate verdict was wrong; record a gate fail first")
    task = {
        "id": uuid.uuid4().hex[:12],
        "stage": stage,
        "title": spec.get("title", "(untitled)"),
        "act_as": spec.get("act_as", STAGE_OWNER[stage]),
        "priority": int(spec.get("priority", 5)),
        "payload": spec.get("payload", {}),
        "attempts": 0,
        "created": _now(),
        "history": [],
    }
    _write_task("inbox", task)
    print(json.dumps({"ok": True, "task": task}, ensure_ascii=False, indent=2))


def cmd_next(_args):
    project = _load_project()
    if not project:
        sys.exit('no project — start one: orchestrator.py new "<Game Name>"')
    stage = current_stage()
    if stage is None:
        print(json.dumps({"done": True, "note": "all 21 gates passed — project complete"},
                         ensure_ascii=False))
        return
    eligible = [t for t in _tasks("inbox") if t.get("stage") == stage]
    active = [t for t in _tasks("active") if t.get("stage") == stage]
    if not eligible:
        note = (f"no inbox tasks for current stage '{stage}'. "
                + (f"{len(active)} task(s) still active. " if active else "")
                + (f"If the stage is truly done, pass its gate: orchestrator.py gate {stage} pass"
                   if not active else "Finish active tasks first (done|fail <id>)."))
        print(json.dumps({"task": None, "stage": stage, "gate": STAGE_GATE[stage],
                          "note": note}, ensure_ascii=False, indent=2))
        return
    task = sorted(eligible, key=lambda t: (-t.get("priority", 5), t.get("created", "")))[0]
    _task_path("inbox", task["id"]).unlink()
    task["history"].append({"ts": _now(), "event": "dispatched"})
    _write_task("active", task)
    print(json.dumps({
        "task": task,
        "stage": stage,
        "act_as": task["act_as"],
        "agent_file": f".claude/agents/{task['act_as']}.md",
        "gate": STAGE_GATE[stage],
        "note": "invoke this agent via the Task tool (subagent_type = act_as); "
                "then orchestrator.py done|fail " + task["id"],
    }, ensure_ascii=False, indent=2))


def cmd_done(args):
    if not args:
        sys.exit("usage: orchestrator.py done <task-id>")
    task_id = args[0]
    q, p = _find_task(task_id)
    if q != "active":
        sys.exit(f"task {task_id} is not active (found in: {q})")
    task = json.loads(p.read_text())
    p.unlink()
    task["history"].append({"ts": _now(), "event": "done"})
    _write_task("done", task)
    print(json.dumps({"ok": True, "task": task_id, "stage": task["stage"],
                      "open_in_stage": len(_open_tasks_for_stage(task["stage"]))},
                     ensure_ascii=False))


def cmd_fail(args):
    if not args:
        sys.exit("usage: orchestrator.py fail <task-id> [reason]")
    task_id, reason = args[0], " ".join(args[1:]) or "unspecified"
    q, p = _find_task(task_id)
    if q != "active":
        sys.exit(f"task {task_id} is not active (found in: {q})")
    task = json.loads(p.read_text())
    p.unlink()
    task["attempts"] = task.get("attempts", 0) + 1
    task["history"].append({"ts": _now(), "event": "fail", "reason": reason})
    memory.append("bugs", {"task": task_id, "stage": task["stage"],
                           "attempt": task["attempts"], "reason": reason})
    if task["attempts"] >= MAX_ATTEMPTS:
        task["escalated"] = True
        _write_task("failed", task)
        memory.append("decisions", {
            "kind": "escalation", "task": task_id, "stage": task["stage"],
            "note": f"{MAX_ATTEMPTS} self-repair cycles exhausted — "
                    "technical-director must brief the Creative Director"})
        print(json.dumps({"ok": True, "escalated": True, "task": task_id,
                          "note": f"ESCALATION: {MAX_ATTEMPTS} attempts exhausted. "
                                  "Stop. Brief the Creative Director with options "
                                  "(see os/pipelines/self_repair.md)."},
                         ensure_ascii=False, indent=2))
    else:
        _write_task("inbox", task)
        print(json.dumps({"ok": True, "requeued": True, "task": task_id,
                          "attempt": task["attempts"], "of": MAX_ATTEMPTS,
                          "note": "self-repair: diagnose root cause before retrying "
                                  "(os/pipelines/self_repair.md)"},
                         ensure_ascii=False, indent=2))


def cmd_gate(args):
    if len(args) < 2 or args[1] not in ("pass", "fail"):
        sys.exit("usage: orchestrator.py gate <stage> pass|fail [note]")
    stage, verdict, note = args[0], args[1], " ".join(args[2:])
    if stage not in STAGE_IDS:
        sys.exit(f"invalid stage '{stage}' — valid: {', '.join(STAGE_IDS)}")
    # gates pass strictly in order
    cur = current_stage()
    if verdict == "pass" and stage != cur:
        sys.exit(f"cannot pass gate '{stage}' — current stage is '{cur}' "
                 "(gates pass strictly in order; no stage may be skipped)")
    open_tasks = _open_tasks_for_stage(stage)
    if verdict == "pass" and open_tasks:
        ids = ", ".join(t["id"] for t in open_tasks)
        sys.exit(f"REFUSED: {len(open_tasks)} open task(s) in stage '{stage}' ({ids}) "
                 "— finish them (done) or fail them; do not edit JSON by hand")
    _ensure_dirs()
    record = {"stage": stage, "status": verdict, "note": note,
              "criteria": STAGE_GATE[stage], "ts": _now()}
    (GATES / f"{stage}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    memory.append("gates", record)
    nxt = current_stage()
    print(json.dumps({"ok": True, "gate": record,
                      "current_stage": nxt or "COMPLETE"}, ensure_ascii=False, indent=2))


def cmd_status(_args):
    project = _load_project()
    passed = [s for s in STAGE_IDS if _gate_passed(s)]
    stage = current_stage()
    out = {
        "project": project,
        "current_stage": stage or "COMPLETE",
        "current_owner": STAGE_OWNER.get(stage) if stage else None,
        "current_gate": STAGE_GATE.get(stage) if stage else None,
        "gates_passed": f"{len(passed)}/{len(STAGE_IDS)}",
        "stages_passed": passed,
        "queue": {q: len(_tasks(q)) for q in ("inbox", "active", "done", "failed")},
        "open_in_current_stage": len(_open_tasks_for_stage(stage)) if stage else 0,
        "escalations": [t["id"] for t in _tasks("failed") if t.get("escalated")],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_stages(_args):
    print(json.dumps([{"stage": s, "act_as": a, "gate": g} for s, a, g in STAGES],
                     ensure_ascii=False, indent=2))


COMMANDS = {"new": cmd_new, "task": cmd_task, "next": cmd_next, "done": cmd_done,
            "fail": cmd_fail, "gate": cmd_gate, "status": cmd_status,
            "stages": cmd_stages}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__.strip())
    _ensure_dirs()
    COMMANDS[sys.argv[1]](sys.argv[2:])
