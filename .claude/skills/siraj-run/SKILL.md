---
name: siraj-run
description: Run N production cycles autonomously (default 5) without stopping after each task.
---

The argument is the number of cycles (default 5). Loop that many times:

1. Perform exactly the /siraj-dispatch procedure (next → Task tool → done|fail).
2. When a stage empties, verify its gate criteria genuinely hold, then
   `orchestrator.py gate <stage> pass` and continue into the next stage.
3. Stop the loop early — regardless of remaining cycles — when:
   - a task escalates (3 failed attempts), or
   - a gate needs Creative Director approval (game_idea plan, visual_qa
     verdicts, publishing sign-off), or
   - Meshy credits would be spent without a logged /siraj-route decision.
4. After the last cycle: one consolidated report — cycles run, stages
   advanced, credits spent, open blockers.

VM discipline still applies between cycles: never overlap heavy Blender work
with a Unity import.
