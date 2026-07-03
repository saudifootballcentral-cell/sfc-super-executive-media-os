---
name: siraj-new
description: Open a new game project: game-director analyzes the idea and presents a development plan for approval.
---

The argument is the game idea (any language). Steps:

1. `python3 os/engine/orchestrator.py status` — if a project is active,
   stop and ask the Creative Director before using `--force`.
2. `python3 os/engine/orchestrator.py new "<Game Name>"` (derive a short
   name from the idea).
3. Seed the first task:
   `python3 os/engine/orchestrator.py task '{"stage":"game_idea","title":"Analyze the idea and draft the development plan","priority":9,"payload":{"idea":"<the full idea text>"}}'`
4. `python3 os/engine/orchestrator.py next` — then invoke the returned agent
   (game-director) via the **Task tool** (`subagent_type: game-director`),
   passing the idea and the boot state. Never do its analysis yourself in the
   main session.
5. Present the plan to the Creative Director for approval. On approval:
   `orchestrator.py done <id>` then `orchestrator.py gate game_idea pass`.

If the idea lacks a GDD, game-director asks exactly 5 questions:
genre, camera, player count, input method, win condition.
