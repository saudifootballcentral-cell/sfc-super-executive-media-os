# Pipeline — QA

Stage: `qa_playtest` · Owner: qa-director

## Protocol
1. Play Mode via MCP; full round start-to-finish; win condition must fire.
2. Console policy: zero errors, zero warnings. **Warning = bug.**
3. Every bug into memory with repro: `memory.py log bugs '{"scene":...,"repro":...,"severity":...}'`.
4. Game feel audit: shake/hit-stop/particles present on every significant event.
5. FPS snapshot into `performance` store (target 60 on the reference machine).

## Gate
Full round playable, win fires, console clean, bugs triaged (open S1/S2 block the gate).

## Escalation
A defect surviving 3 fix attempts escalates via the orchestrator (self_repair.md).
