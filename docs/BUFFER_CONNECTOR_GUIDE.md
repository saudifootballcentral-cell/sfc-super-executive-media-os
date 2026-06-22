# Buffer Connector Guide — Package 9A

## Overview

Buffer is the primary publishing hub for SFC's social media distribution. It handles Instagram, Threads, Facebook, and TikTok. YouTube and X use direct integrations instead.

## Setup

```bash
export BUFFER_ACCESS_TOKEN="your_access_token"
export BUFFER_INSTAGRAM_PROFILE_ID="buf_ig_your_id"
export BUFFER_THREADS_PROFILE_ID="buf_th_your_id"
export BUFFER_FACEBOOK_PROFILE_ID="buf_fb_your_id"
export BUFFER_TIKTOK_PROFILE_ID="buf_tt_your_id"
```

Without `BUFFER_ACCESS_TOKEN`, `service.is_authenticated` returns `False` and all operations run in mock mode.

## Usage

```python
from sfc.connectors.buffer.service import get_buffer_service
from sfc.connectors.buffer.models import BufferPlatform

service = get_buffer_service()
```

### Schedule a post

```python
from datetime import datetime, timedelta

post = await service.create_scheduled_post(
    content="Match day! ⚽ #SaudiFootball",
    platform=BufferPlatform.INSTAGRAM,
    scheduled_at=datetime.utcnow() + timedelta(hours=2),
    media_url="https://cdn.sfc.sa/images/matchday.jpg",
    hashtags=["#SFC", "#SPL"],
)
print(post.status)  # BufferPostStatus.SCHEDULED
```

### Publish immediately

```python
result = await service.publish_post(post.post_id)
print(result.status)  # BufferPostStatus.SENT
print(result.url)     # https://instagram.com/p/buf_instagram_...
```

### Publish to multiple platforms

```python
results = await service.publish_to_platforms(
    content="Goal of the month! 🏆",
    platforms=[BufferPlatform.INSTAGRAM, BufferPlatform.THREADS, BufferPlatform.FACEBOOK],
    media_url="https://cdn.sfc.sa/images/goal.jpg",
    hashtags=["#SFC", "#AlHilal"],
)
assert len(results) == 3
assert all(r.status == BufferPostStatus.SENT for r in results)
```

### Publish a content package

```python
package = {
    "package_type": "instagram",
    "caption": "Match highlights are live! ⚽",
    "hashtags": ["#SFC", "#SPL"],
    "thumbnail_url": "https://cdn.sfc.sa/thumbs/highlights.jpg",
    "ready_to_publish": True,
}
results = await service.publish_content_package(package)
```

Package type → platforms mapping:

| package_type | Platforms |
|-------------|----------|
| `instagram` | INSTAGRAM, THREADS |
| `tiktok` | TIKTOK |
| `youtube_short` | INSTAGRAM, FACEBOOK |
| `podcast` | FACEBOOK, THREADS |
| `x_thread` | _(none — handled by X connector)_ |
| _(default)_ | INSTAGRAM |

### Queue management

```python
queue = await service.get_queue()
print(queue.scheduled_count, queue.sent_count, queue.failed_count)
print(queue.next_publish_at)
```

### Check post status

```python
post = await service.get_status(post_id)
if post:
    print(post.status, post.retry_count)
```

### Retry failed posts

```python
# Retry a specific post
result = await service.retry_failed(post_id)

# Retry all failed posts
results = await service.retry_all_failed()
```

Retries respect `_MAX_RETRIES = 3`. Posts that have exceeded the limit return `BufferPostStatus.FAILED` with an error message.

### Generate report

```python
report = await service.generate_report()
print(f"Published: {report.posts_published}")
print(f"Failed: {report.posts_failed}")
print(f"Retried: {report.posts_retried}")
print(f"Success rate: {report.success_rate}%")
```

## Models

### `BufferPost`

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | str | Internal post ID (UUID) |
| `content` | str | Post text |
| `platform` | BufferPlatform | Target platform |
| `status` | BufferPostStatus | DRAFT/SCHEDULED/SENT/FAILED/RETRYING |
| `scheduled_at` | datetime | Scheduled publish time |
| `retry_count` | int | Number of retry attempts |
| `platform_post_id` | str | Platform's post ID after publishing |

### `BufferPlatform`

| Value | Platform |
|-------|---------|
| `instagram` | Instagram |
| `threads` | Threads |
| `facebook` | Facebook |
| `tiktok` | TikTok |
| `linkedin` | LinkedIn |

### `BufferConnectorReport`

| Field | Description |
|-------|-------------|
| `posts_created` | Total posts created |
| `posts_published` | Posts successfully sent |
| `posts_failed` | Posts that failed |
| `posts_retried` | Posts that needed retry |
| `platforms_active` | List of platforms used |
| `success_rate` | Float, 0-100 |
| `api_errors` | API error count |
| `rate_limit_hits` | Rate limit hit count |

## Retry Logic

Buffer uses a simple retry system:

1. `retry_failed(post_id)` — increments `retry_count`, sets status to RETRYING, then publishes
2. If `retry_count >= _MAX_RETRIES` (3), returns FAILED with error message
3. `retry_all_failed()` — calls `retry_failed()` for every post with status FAILED

## Observability

```python
service.observability.connector        # "buffer"
service.observability.success_rate     # float, 0-100
service.observability.avg_latency_ms   # float
service.observability.api_errors       # int
service.observability.rate_limit_hits  # int
```
