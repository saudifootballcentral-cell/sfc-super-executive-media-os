# SFC Super Executive Media OS

Autonomous executive operating system for an AI-native Saudi football sports media company.

## Architecture

```
core/           — Models, event bus, memory layers, knowledge graph, executive orchestrator
agentops/       — Agent/Prompt/Capability/Tool registries + Health/Cost/Quality monitors
divisions/      — Nine operating divisions (intelligence, editorial, creative, etc.)
war_rooms/      — Specialized command centers (match day, transfer window, world cup, crisis)
reporting/      — Executive reports (daily, weekly, monthly, quarterly, annual)
config/         — settings.yaml, platforms.yaml
constitution/   — OFFICIAL_CONSTITUTION.md (source of truth for all rules)
tests/          — Pytest suite enforcing constitutional rules
```

## Key constitutional rules enforced in code

- **Verification Policy**: `ContentItem.is_publishable` requires `len(sources) >= 2`
- **Confidence Policy**: `OutputScores.requires_escalation` is `True` when `confidence_score < 85`
- **Publishing Policy**: `GovernanceDivision.review_content()` gates all content; `PublishingDivision.publish()` blocks non-approved content
- **Event Pipeline**: `EventBus` routes events through Intelligence → Editorial → Creative → Governance → Publishing → Analytics

## Running

```bash
pip install -r requirements.txt
python main.py          # demo boot + news event
pytest tests/           # constitutional compliance tests
```

## Entry point

`core/executive.py:SFCExecutive` — instantiate once; all divisions, memory, and agentops attach to it.

## Mandatory workflow

Every piece of content must pass through all 10 stages (defined in `EventBus.PIPELINE_ORDER`):

```
Discovery → Verification → Prioritization → Planning → Content
→ Creative → Governance → Publishing → Analytics → Learning
```

No stage may be skipped.
