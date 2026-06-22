# YouTube Connector Guide — Package 9A

## Overview

The YouTube connector provides direct integration with YouTube Data API v3. It handles video/Shorts publishing, metadata management, playlist creation, analytics reading, and channel metrics.

## Setup

```bash
export YOUTUBE_CLIENT_ID="your_client_id"
export YOUTUBE_CLIENT_SECRET="your_client_secret"
export YOUTUBE_CHANNEL_ID="UCyour_channel_id"
```

Without these vars set, `service.is_authenticated` returns `False` and all operations run in mock mode.

## Usage

```python
from sfc.connectors.youtube.service import get_youtube_service
from sfc.connectors.youtube.models import VideoUploadRequest, VideoPrivacy, VideoCategory

service = get_youtube_service()
```

### Upload a video

```python
req = VideoUploadRequest(
    title="SPL Round 15 Highlights",
    description="Best goals from matchday 15",
    tags=["SPL", "Saudi Football", "AlHilal"],
    category=VideoCategory.SPORTS,
    privacy=VideoPrivacy.PUBLIC,
    file_url="https://cdn.sfc.sa/videos/round15.mp4",
    thumbnail_url="https://cdn.sfc.sa/thumbs/round15.jpg",
    language="ar",
)
result = await service.upload_video(req)
print(result.url)  # https://www.youtube.com/watch?v=...
```

### Upload a Short

```python
req = VideoUploadRequest(title="Goal of the Week", is_short=True)
result = await service.upload_short(req)
assert result.is_short is True
```

### Update metadata

```python
await service.update_metadata(
    video_id="abc123",
    title="Updated Title",
    description="Updated description",
    tags=["new", "tags"],
)
```

### Create a playlist

```python
playlist = await service.create_playlist(
    title="SPL Season 2025 Highlights",
    description="All goals and highlights",
    video_ids=["vid1", "vid2", "vid3"],
)
print(playlist.url)
```

### Read analytics

```python
analytics = await service.get_analytics("vid_abc123")
print(analytics.views, analytics.ctr, analytics.watch_time_hours)
```

### Channel metrics

```python
metrics = await service.get_channel_metrics()
print(metrics.subscriber_count, metrics.monthly_views)
```

### Generate report

```python
report = await service.generate_report()
print(f"Published: {report.videos_published} videos, {report.shorts_published} shorts")
```

## Models

### `VideoUploadRequest`

| Field | Type | Default |
|-------|------|---------|
| `title` | str | required |
| `description` | str | `""` |
| `tags` | list[str] | `[]` |
| `category` | VideoCategory | SPORTS |
| `privacy` | VideoPrivacy | PUBLIC |
| `file_url` | str | `""` |
| `thumbnail_url` | str | `""` |
| `is_short` | bool | False |
| `language` | str | `"ar"` |
| `made_for_kids` | bool | False |

### `VideoPublishResult`

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | str | YouTube video ID |
| `url` | str | Full YouTube watch URL |
| `status` | UploadStatus | PUBLISHED / PROCESSING / FAILED |
| `is_short` | bool | Whether it's a Short |
| `published_at` | datetime | Publication timestamp |

### `YouTubeAnalytics`

| Field | Type | Description |
|-------|------|-------------|
| `views` | int | Total view count |
| `impressions` | int | Impression count |
| `ctr` | float | Click-through rate (%) |
| `watch_time_hours` | float | Total watch time |
| `likes` | int | Like count |
| `subscribers_gained` | int | New subscribers from video |

## Observability

```python
service.observability.success_rate     # float, 0-100
service.observability.avg_latency_ms   # float
service.observability.api_errors       # int
service.observability.rate_limit_hits  # int
```
