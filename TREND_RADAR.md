# Trend Radar Engine

Detects and classifies social media trends across Saudi football platforms.

## 7-State Lifecycle

```
BREAKING → EMERGING → RISING → HOT → PEAK → DECLINING → DEAD
```

- **BREAKING**: velocity > 8 — immediate response required
- **EMERGING**: newly detected trend gaining traction
- **RISING**: growing volume and velocity
- **HOT**: high engagement, velocity > 6
- **PEAK**: maximum reach/engagement
- **DECLINING**: losing momentum
- **DEAD**: no longer trending

## Metrics

| Metric | Description |
|--------|-------------|
| `velocity` | Rate of mention growth per hour |
| `volume` | Total mentions in tracking window |
| `acceleration` | Rate of velocity change |
| `reach` | Estimated unique user reach |
| `engagement` | Engagement rate (likes/shares/comments) |

## Platforms Monitored

X, Instagram, TikTok, YouTube, Reddit, Google Trends, Forums, News

## Usage

```python
from sfc.social.trend_radar.service import get_trend_radar

radar = get_trend_radar()
snapshot = await radar.scan(topics=["Al Hilal Champions"])
print(snapshot.top_topic, snapshot.top_score)
```

## Singleton

`get_trend_radar()` — returns process-level singleton.
