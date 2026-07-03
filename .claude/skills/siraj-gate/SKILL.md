---
name: siraj-gate
description: Pass or fail a stage gate — only after genuinely verifying the gate criteria.
---

Arguments: `<stage> pass|fail [note]`.

1. `python3 os/engine/orchestrator.py status` — confirm the stage is current.
2. Verify the gate criteria **against reality** (logs, files, Play Mode,
   screenshots — whatever the criteria name), not against intentions.
   The criteria string is in `orchestrator.py stages`.
3. `python3 os/engine/orchestrator.py gate <stage> pass|fail "<evidence>"`.
4. The engine refuses a pass while open tasks exist in the stage — that
   refusal is correct; finish or fail the tasks. Never edit queue/gate JSON
   by hand.

Gates that additionally need explicit Creative Director words before `pass`:
`game_idea` (plan approval), `visual_qa` (asset approval), `publishing`
(final sign-off).
