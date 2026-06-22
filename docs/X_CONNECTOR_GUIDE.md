# X Connector Guide — Package 9A

## Overview

The X connector provides direct integration with X API v2. It handles post and thread publishing, media upload, social intelligence monitoring (trends, keywords, hashtags, conversations), and analytics.

## Setup

```bash
export X_API_KEY="your_api_key"
export X_API_SECRET="your_api_secret"
export X_ACCESS_TOKEN="your_access_token"
export X_ACCESS_SECRET="your_access_secret"
```

Without these vars, `service.is_authenticated` returns `False` and all operations use mock data.

## Usage

```python
from sfc.connectors.x.service import get_x_service

service = get_x_service()
```

### Create a post

```python
post = await service.create_post("SPL Round 15 kicks off! 🏟️ #SaudiProLeague")
print(post.url)  # https://x.com/sfc/status/...
```

Posts exceeding 280 characters return status `XPostStatus.FAILED`.

### Create a thread

```python
thread = await service.create_thread(
    texts=[
        "🔥 Transfer Analysis Thread: Why AlHilal's latest signing changes everything...",
        "1/ The tactical fit: Here's how the new player slots into the 4-3-3...",
        "2/ The numbers: 25 goals, 12 assists in 30 games — elite production...",
        "3/ Bottom line: This is a statement signing for #SaudiProLeague. 🇸🇦",
    ],
    topic="Transfer Analysis",
)
print(thread.total_posts)  # 4
```

### Upload media

```python
from sfc.connectors.x.models import XMediaType

media = await service.upload_media(
    file_url="https://cdn.sfc.sa/images/goal.jpg",
    media_type=XMediaType.IMAGE,
    alt_text="Goal celebration",
)
post = await service.create_post("What a finish! 🎯", media_ids=[media.platform_media_id])
```

### Schedule a post

```python
from datetime import datetime, timedelta

future = datetime.utcnow() + timedelta(hours=3)
post = await service.schedule_post("Match preview — 3 hours until kickoff!", scheduled_at=future)
assert post.status == XPostStatus.SCHEDULED
```

### Social intelligence

```python
# Trending topics (Saudi-focused, sorted by volume descending)
trends = await service.get_trending_topics()
for t in trends[:5]:
    print(t.term, t.tweet_volume)

# Monitor keywords
kw_trends = await service.monitor_keywords(["SPL", "AlHilal", "transfer"])

# Monitor hashtags
ht_trends = await service.monitor_hashtags(["#SaudiProLeague", "#الدوري_السعودي"])

# Search conversations
convs = await service.search_conversations("Saudi football", max_results=10)
for c in convs:
    print(c.query, c.tweet_count)
```

## Models

### `XPost`

| Field | Type | Description |
|-------|------|-------------|
| `text` | str | Post content (≤280 chars) |
| `platform_post_id` | str | X platform post ID |
| `status` | XPostStatus | PUBLISHED / SCHEDULED / FAILED |
| `url` | str | Full post URL |
| `media_ids` | list[str] | Attached media IDs |

### `XThread`

| Field | Type | Description |
|-------|------|-------------|
| `topic` | str | Thread topic |
| `posts` | list[XPost] | Individual posts in order |
| `total_posts` | int | Post count |
| `platform_thread_root_id` | str | Root post's platform ID |

### `XTrend`

| Field | Type | Description |
|-------|------|-------------|
| `term` | str | Hashtag or keyword |
| `tweet_volume` | int | Current tweet volume |
| `category` | str | Trend category |

### `XMetrics`

| Field | Type | Description |
|-------|------|-------------|
| `views` | int | View count |
| `impressions` | int | Impression count |
| `likes` | int | Like count |
| `retweets` | int | Retweet count |
| `engagement_rate` | float | Engagement rate (%) |

## Social Intelligence Feed

The X connector node writes live trend data to `trend_radar_data` state key on every pipeline run, making it available to:
- **Package 8B** — Social Intelligence & Trend Analysis Engine
- **Package 8C** — Narrative Intelligence & Audience Modeling Engine

```python
# In x_connector_node.py
return {
    "trend_radar_data": {
        "live_trends": trend_dicts,   # list of XTrend dicts
        "top_trend": trends[0].term,  # string
    },
    ...
}
```

## Monitor Config

```python
from sfc.connectors.x.models import XMonitorConfig

cfg = XMonitorConfig()
# Defaults:
# cfg.languages == ["ar", "en"]
# cfg.geo == "SA"
# cfg.result_type == "recent"
```
