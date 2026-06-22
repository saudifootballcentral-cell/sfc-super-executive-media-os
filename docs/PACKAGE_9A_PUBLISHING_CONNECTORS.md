# Package 9A — MVP Publishing & Intelligence Connectors

## Overview

Package 9A connects SFC to real-world publishing and intelligence platforms. It sits after the Creative Production Graph (8E) and is gated by governance approval — only content with `ready_to_publish=True` is published.

## Architecture

```
START
  → youtube_connector    Upload videos/Shorts + channel analytics
  → x_connector          Post threads + social intelligence feed
  → buffer_connector     Route to Instagram/Threads/Facebook/TikTok
  → analytics_sync       Aggregate metrics + update historical store
END
```

## Connectors

| Connector | Platform | Role |
|-----------|----------|------|
| YouTube | Direct integration | Video/Shorts publishing + channel analytics |
| X (Twitter) | Direct integration | Posts/threads + social intelligence feed |
| Buffer | Publishing hub | Routes to Instagram, Threads, Facebook, TikTok |
| Analytics Sync | Aggregator | Cross-platform metrics, growth, trend history |

## Governance Contract

All connector nodes enforce the governance gate:

```python
# Only process packages approved by governance
packages = [
    p for p in content_packages
    if p.get("ready_to_publish", False)
]
```

This graph **never bypasses**: Constitution, Governance, Executive Approval, or Publishing Controls.

## Social Intelligence Feed

The X connector writes live trend data back to `trend_radar_data` for consumption by Packages 8B and 8C:

```python
return {
    "trend_radar_data": {
        "live_trends": trend_dicts,
        "top_trend": trends[0].term,
    },
    ...
}
```

## Secrets

All credentials are read from environment variables — never hardcoded:

| Variable | Purpose |
|----------|---------|
| `YOUTUBE_CLIENT_ID` | YouTube OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth client secret |
| `YOUTUBE_CHANNEL_ID` | Target channel ID |
| `X_API_KEY` | X API v2 key |
| `X_API_SECRET` | X API v2 secret |
| `X_ACCESS_TOKEN` | X access token |
| `X_ACCESS_SECRET` | X access token secret |
| `BUFFER_ACCESS_TOKEN` | Buffer API token |
| `BUFFER_INSTAGRAM_PROFILE_ID` | Buffer Instagram profile |
| `BUFFER_THREADS_PROFILE_ID` | Buffer Threads profile |
| `BUFFER_FACEBOOK_PROFILE_ID` | Buffer Facebook profile |
| `BUFFER_TIKTOK_PROFILE_ID` | Buffer TikTok profile |

## State Keys

Package 9A reads and writes these `SFCState` keys:

| Key | Direction | Description |
|-----|-----------|-------------|
| `content_packages` | Read | Packages from 8E to publish |
| `youtube_results` | Write | YouTube publish results + channel metrics |
| `x_results` | Write | X post results + social intelligence |
| `buffer_queue_state` | Write | Buffer queue status + publish results |
| `analytics_data` | Write | Cross-platform analytics sync report |
| `trend_radar_data` | Write | Live X trends for 8B/8C consumption |
| `historical_analytics` | Read+Write | Cumulative analytics history |

## Events

| Event | Trigger |
|-------|---------|
| `VideoPublished` | YouTube video or Short uploaded |
| `AnalyticsUpdated` | Analytics sync completed |
| `ChannelGrowthUpdated` | Channel growth metrics refreshed |
| `XPostPublished` | X post published |
| `XThreadPublished` | X thread published |
| `XConversationDetected` | Conversation matching keywords found |
| `BufferPostCreated` | Post scheduled in Buffer |
| `BufferPostPublished` | Buffer post sent to platform |
| `BufferPostFailed` | Buffer post failed after retries |

## Mock Behavior

All external API calls are mocked. Services function identically with or without real credentials:

- `YouTubeService.upload_video()` — returns a realistic `VideoPublishResult` with a generated video ID
- `XService.create_post()` — validates 280-char limit; returns `XPost` with mock platform ID
- `BufferService.publish_to_platforms()` — creates posts and marks them SENT
- `AnalyticsSyncService.generate_sync_report()` — pulls from YouTube and X mock analytics

## Running

```bash
# Run Package 9A tests only
pytest tests/connectors/ tests/integration/test_pkg9a_e2e.py -v

# Run full suite
pytest tests/ -v
```
