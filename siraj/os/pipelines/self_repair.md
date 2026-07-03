# Pipeline — Self-repair

Applies to every stage. The orchestrator enforces it mechanically.

## The loop
1. `orchestrator.py fail <id> "<root cause>"` — task returns to inbox, attempt++.
2. Before retrying, the assigned agent must DIAGNOSE, not re-run: read the error, the
   relevant OPS_LESSONS section, and the memory `bugs` history for this task.
3. Each retry must change something identifiable (prompt, script, config) — a retry
   without a diff is forbidden.
4. Attempt 3 fails ⇒ task moves to `queue/failed/` with `escalated: true`; a decision
   entry is logged automatically.

## Escalation
technical-director reviews the three attempts and briefs the Creative Director with at
least two options (e.g. reroute the asset, cut the feature, change the approach) and a
recommendation. No further attempts before a decision.

## Known fast paths
Meshy deform → prompt fix (max 2) → procedural. FBX scale → meshy_refine.py. Unity OOM →
NOGFX restart. FPS → particles → decimate → shaders → count (in that order).
