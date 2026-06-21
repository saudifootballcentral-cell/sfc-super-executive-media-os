# Social War Room

Activates and manages crisis response for Saudi football social media events.

## 7 Triggers

| Trigger | Priority | Description |
|---------|----------|-------------|
| `SENTIMENT_CRISIS` | P1 | Fan sentiment crashes below -50 |
| `NATIONAL_TEAM_CRISIS` | P1 | Green Falcons reputation at risk |
| `MEDIA_ATTACK` | P1 | Coordinated media attack detected |
| `BREAKING_STORY` | P2 | High-velocity breaking news |
| `NARRATIVE_SPIKE` | P2 | Sudden narrative shift or spike |
| `TRANSFER_EXPLOSION` | P3 | Transfer rumour explosion |
| `REFEREE_CONTROVERSY` | P3 | Referee/VAR controversy trending |

## Priority Levels

- **P1 — Critical**: Immediate response, executive approval required, all publishing halted
- **P2 — High**: Response within 1 hour
- **P3 — Medium**: Response within 4 hours

## Response Components

Each war room report includes:
- `recommended_responses` — immediate action steps
- `narrative_strategies` — counter-narrative playbook
- `executive_alerts` — escalation notices
- `persona_assignments` — role assignments for each crisis persona

## Governance Rule

**No war room content may be published without passing through `governance_node`.** War room activations trigger autonomous execution which routes through the full 10-stage pipeline.

## Usage

```python
from sfc.social.war_room.service import get_war_room_service
from sfc.social.war_room.models import SocialWarRoomTrigger

svc = get_war_room_service()
should_activate = await svc.evaluate(SocialWarRoomTrigger.SENTIMENT_CRISIS, context={"sentiment_score": -70})
if should_activate:
    state = await svc.activate(SocialWarRoomTrigger.SENTIMENT_CRISIS)
    report = await svc.generate_report(state)
    await svc.resolve(state.war_room_id)
```
