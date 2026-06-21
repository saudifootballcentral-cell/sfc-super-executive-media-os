# Fan Sentiment Engine

Measures fan emotion across Saudi football entities in real-time.

## Sentiment Categories

| Category | Score Range |
|----------|-------------|
| POSITIVE | score > 20 |
| NEUTRAL  | -20 ≤ score ≤ 20 |
| NEGATIVE | score < -20 |

## Target Types

PLAYER, COACH, CLUB, COMPETITION, SPONSOR, NATIONAL_TEAM

## Metrics

| Metric | Range | Description |
|--------|-------|-------------|
| `score` | -100–100 | Current sentiment score |
| `momentum` | float | Rate of change per hour |
| `volatility` | 0–100 | Variability of recent scores |
| `confidence` | 0–100 | Measurement confidence |
| `sample_size` | int | Data points analyzed |

## Crisis Threshold

Entities with score < -50 trigger `SENTIMENT_CRISIS` alerts and activate the Social War Room.

## Usage

```python
from sfc.social.sentiment.service import get_sentiment_service

svc = get_sentiment_service()
targets = await svc.analyze(entity_ids=["al_hilal_club"])
report = await svc.generate_fan_pulse_report(targets)
dashboard = report.to_dashboard_data()
```
