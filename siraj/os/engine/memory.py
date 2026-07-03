#!/usr/bin/env python3
"""
memory.py — Siraj's sole writer of persistent memory.

Every durable fact about the studio lives in memory/<store>.json as an
append-only list of timestamped entries. Nothing else in the system may
write these files (ADR-002: file-based state, one writer per file).

Stores:
  assets         imported/produced assets (name, route, polys, path, project)
  meshy_history  every Meshy task fired (prompt, task_id, kind, cost)
  credits        Meshy credit spend/refill events
  bugs           defects found + their fix status
  performance    fps/profiler snapshots per scene
  decisions      routed/architectural decisions (who, why, alternatives)
  scenes         scene inventory per project
  versions       build + activation events
  gates          stage gate pass/fail records (orchestrator writes via us)

Usage:
  python3 memory.py boot                       # state summary (JSON)
  python3 memory.py log <store> '<json>'       # append one entry
  python3 memory.py read <store> [n]           # last n entries (default 10)
  python3 memory.py count <store>              # entry count
"""
import json
import os
import sys
import time
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent          # .../os/engine
OS_DIR = ENGINE_DIR.parent                            # .../os (or siraj-os)
ROOT = Path(os.environ.get("SIRAJ_ROOT", OS_DIR.parent))
MEMORY_DIR = Path(os.environ.get("SIRAJ_MEMORY_DIR", ROOT / "memory"))
RUNTIME_DIR = OS_DIR / "runtime"

STORES = (
    "assets", "meshy_history", "credits", "bugs", "performance",
    "decisions", "scenes", "versions", "gates",
)


def _store_path(store: str) -> Path:
    if store not in STORES:
        sys.exit(f"unknown store '{store}' — valid: {', '.join(STORES)}")
    return MEMORY_DIR / f"{store}.json"


def read_store(store: str) -> list:
    path = _store_path(store)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        sys.exit(f"corrupt store {path} — fix or move it aside before continuing")
    return data if isinstance(data, list) else []


def append(store: str, entry: dict) -> dict:
    if not isinstance(entry, dict):
        sys.exit("entry must be a JSON object")
    entries = read_store(store)
    entry = dict(entry)
    entry.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    entries.append(entry)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _store_path(store)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)
    return entry


def _queue_counts() -> dict:
    counts = {}
    for q in ("inbox", "active", "done", "failed"):
        d = RUNTIME_DIR / "queue" / q
        counts[q] = len(list(d.glob("*.json"))) if d.is_dir() else 0
    return counts


def boot() -> dict:
    """Where are we? The one call every session starts with."""
    project_file = RUNTIME_DIR / "project.json"
    project = None
    if project_file.exists():
        try:
            project = json.loads(project_file.read_text())
        except json.JSONDecodeError:
            project = {"error": f"corrupt {project_file}"}
    summary = {
        "memory_dir": str(MEMORY_DIR),
        "project": project,
        "queue": _queue_counts(),
        "stores": {},
    }
    for store in STORES:
        entries = read_store(store)
        summary["stores"][store] = {
            "count": len(entries),
            "last": entries[-1] if entries else None,
        }
    return summary


def main(argv):
    if not argv:
        sys.exit(__doc__.strip())
    cmd, args = argv[0], argv[1:]
    if cmd == "boot":
        print(json.dumps(boot(), ensure_ascii=False, indent=2))
    elif cmd == "log":
        if len(args) < 2:
            sys.exit("usage: memory.py log <store> '<json>'")
        try:
            entry = json.loads(args[1])
        except json.JSONDecodeError as e:
            sys.exit(f"invalid JSON: {e}")
        print(json.dumps(append(args[0], entry), ensure_ascii=False))
    elif cmd == "read":
        n = int(args[1]) if len(args) > 1 else 10
        print(json.dumps(read_store(args[0])[-n:], ensure_ascii=False, indent=2))
    elif cmd == "count":
        print(len(read_store(args[0])))
    else:
        sys.exit(f"unknown command '{cmd}' — see: python3 memory.py")


if __name__ == "__main__":
    main(sys.argv[1:])
