# Video Ingestion Setup

## Supported Input Sources

| Source Type | Enum | Description |
|---|---|---|
| `local_mp4` | `VideoSourceType.LOCAL_MP4` | Local MP4 file |
| `local_mov` | `VideoSourceType.LOCAL_MOV` | Local MOV file |
| `youtube_url` | `VideoSourceType.YOUTUBE_URL` | YouTube video URL |
| `uploaded_file` | `VideoSourceType.UPLOADED_FILE` | Operator-uploaded video |
| `press_conference` | `VideoSourceType.PRESS_CONFERENCE` | Press conference recording |
| `interview` | `VideoSourceType.INTERVIEW` | Player/coach interview |
| `podcast_video` | `VideoSourceType.PODCAST_VIDEO` | Video podcast |
| `match_recording` | `VideoSourceType.MATCH_RECORDING` | Full match recording |
| `training_video` | `VideoSourceType.TRAINING_VIDEO` | Training session |
| `club_media` | `VideoSourceType.CLUB_MEDIA` | Club-produced media |

---

## Rights Status

| Status | Processing | Publishing |
|---|---|---|
| `owned` | Full | Allowed |
| `licensed` | Full | Allowed |
| `public_source` | Full | Allowed |
| `unknown` | Internal analysis only | **Blocked** until operator approval |
| `restricted` | **Blocked** immediately | **Blocked** |

Restricted sources are rejected at ingestion. Unknown-rights sources are
analyzed internally but governance blocks publishing.

---

## Deduplication

Every ingested video is SHA-256 hashed. If a duplicate hash is detected,
`VideoIngestionResult.is_duplicate = True` and `duplicate_of` is set to the
original video ID. Processing stops — no duplicate clips are created.

For URL-based sources (no local file), the URL string is hashed instead.

---

## Metadata Extraction

When `VIDEO_PROCESSING_ENABLED=true` and `ffprobe` is available:

```bash
which ffprobe  # must return a path
```

Extracted fields: `duration_seconds`, `fps`, `file_size_bytes`, `codec`,
`bitrate_kbps`, `resolution` (width × height).

When ffprobe is unavailable, metadata defaults are used (1920×1080, 30fps).

---

## Example

```python
from sfc.video_intelligence.ingestion.models import VideoSource, VideoSourceType, RightsStatus
from sfc.video_intelligence.ingestion.service import get_video_ingestion_service

svc = get_video_ingestion_service()
source = VideoSource(
    source_type=VideoSourceType.MATCH_RECORDING,
    path="/media/spl/match_2026_06_22.mp4",
    title="Al-Hilal vs Al-Nassr — SPL Final",
    rights_status=RightsStatus.OWNED,
)
result = await svc.ingest(source)
print(result.status)                   # VideoProcessingStatus.ANALYZING
print(result.video_metadata.duration_label)  # 1:32:15
```
