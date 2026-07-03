---
name: siraj-dispatch
description: Dispatch one production cycle: pull the next task and hand it to the owning agent via the Task tool.
---

One cycle, fully supervised:

1. `python3 os/engine/orchestrator.py next`
2. If `task` is null: follow the `note` (either pass the gate after a real
   verification against its criteria, or ask the Creative Director what to
   queue). Stop.
3. Read the returned agent contract (`.claude/agents/<act_as>.md`) if in any
   doubt about its authority.
4. Invoke that agent via the **Task tool** (`subagent_type` = `act_as`),
   passing: the task JSON, current project state (`memory.py boot`), and the
   stage's gate criteria. Never execute the agent's work in the main session.
5. On verified success: `python3 os/engine/orchestrator.py done <id>`.
   On failure: `python3 os/engine/orchestrator.py fail <id> "<root cause>"` —
   the engine handles the self-repair loop (3 attempts → escalation).
6. Report the cycle result in one short paragraph.
