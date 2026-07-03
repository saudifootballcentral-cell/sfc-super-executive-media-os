# Siraj OS — Roadmap (7 controlled phases)

Phases 1–4 are shipped in this package. Phases 5–7 are deliberately built
*inside real game projects* — infrastructure invented without a game to
prove it is scope creep.

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Production triangle: meshy_client → meshy_refine → siraj-build.sh → SirajBridge/Postprocessor | ✅ shipped |
| 2 | Engine: orchestrator (21 stages, gates, self-repair), asset router (routing law), memory (9 stores) | ✅ shipped |
| 3 | Roles: 27 agent contracts (os/agents) + Claude Code subagents + /siraj-* skills + secrets guard | ✅ shipped |
| 4 | Unity account & cloud integrations: license cycle, Asset Manager bridge, UGS deploy, Unity VCS, cloud-build hook | ✅ shipped |
| 5 | First full production run: one complete game through all 21 gates; harden every pipeline doc against reality | 🔜 in-project |
| 6 | Quality flywheel: performance baselines in memory, playtest heuristics, prompt library per art style | 🔜 in-project |
| 7 | Scale: multi-project memory, cross-game asset reuse index, marketplace route automation | 🔜 in-project |

Rules:
- No phase 5–7 work before a real game demands it.
- Every phase lands with its self-test wired into `siraj-activate.sh`.
