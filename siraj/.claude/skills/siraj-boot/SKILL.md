---
name: siraj-boot
description: Boot Siraj: read real project state from the engine (never from memory of past chats). Run first in every session.
---

Run these and read the output — they are the sole source of truth:

```bash
python3 os/engine/memory.py boot
python3 os/engine/orchestrator.py status
```

Then report to the Creative Director, briefly:
1. Active project (or "none — start one with /siraj-new").
2. Current stage, its owner agent, and its gate criteria.
3. Queue counts (inbox/active/done/failed) and any escalations — escalations
   are read aloud first, they block everything.
4. Anything abnormal in the last entries of `bugs`, `credits`, or `gates`.

Do NOT assume state from earlier conversation. If `memory.py boot` fails,
stop and diagnose before any other work (see os/OPS_LESSONS.md).
