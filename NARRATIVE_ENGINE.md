# Narrative Intelligence Engine

Tracks narrative lifecycles across Saudi football media ecosystem.

## 5-State Lifecycle

```
EMERGING → GROWING → PEAKING → DECLINING → DORMANT
```

## Narrative Categories

- PLAYER, CLUB, NATIONAL_TEAM, TRANSFER, TOURNAMENT
- REFEREE, SPONSOR, MEDIA, GENERAL

## Metrics

| Metric | Range | Description |
|--------|-------|-------------|
| `score` | 0–100 | Overall narrative strength |
| `growth_rate` | % | Monthly growth rate |
| `velocity` | 0–10 | Speed of narrative spread |
| `sentiment` | -1–1 | Tone of narrative |
| `influence` | 0–1 | Reach to key decision-makers |
| `reach` | int | Estimated audience size |

## Conflict Detection

The `build_narrative_map()` method detects narrative conflicts — pairs of narratives with sentiment difference > 0.7, which may require crisis management.

## Usage

```python
from sfc.social.narrative.service import get_narrative_service

svc = get_narrative_service()
narratives = await svc.detect_narratives(topics=["Transfer saga"])
report = await svc.generate_report(narratives)
```
