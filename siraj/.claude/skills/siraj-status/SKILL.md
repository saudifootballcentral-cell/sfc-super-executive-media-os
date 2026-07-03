---
name: siraj-status
description: Read-only full status report: project, stage, queue, gates, credits, bugs. Changes nothing.
---

Strictly read-only — no state changes, no gate passes, no dispatches.

```bash
python3 os/engine/orchestrator.py status
python3 os/engine/memory.py boot
python3 os/engine/memory.py read credits 5
python3 os/engine/memory.py read bugs 5
python3 os/engine/memory.py read gates 5
```

Report: project · current stage/owner/gate · gates passed (n/21) · queue
counts · escalations · credits picture · recent bugs. One screen, no fluff,
both languages welcome — mirror the Creative Director's language.
