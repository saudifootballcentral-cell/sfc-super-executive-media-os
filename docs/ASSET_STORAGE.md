# Asset Storage

## Directory Structure

```
artifacts/creative/
    images/          ← generated image files (.png / .jpg)
    thumbnails/      ← generated thumbnail files (.png / .jpg)
    audio/           ← generated audio files (.mp3)
    manifests/       ← per-asset JSON manifest files
```

Default root: `./artifacts/creative`  
Override: `CREATIVE_STORAGE_PATH=/path/to/storage`

---

## Per-Asset Manifest

For every successfully generated asset a JSON manifest is written to
`manifests/{asset_id}.json`:

```json
{
  "asset_id": "uuid",
  "asset_type": "image",
  "provider": "flux",
  "status": "generated",
  "local_path": "artifacts/creative/images/uuid.jpg",
  "public_url": null,
  "mime_type": "image/jpeg",
  "file_size": 204800,
  "checksum_sha256": "abc123...",
  "prompt": "...",
  "negative_prompt": "...",
  "created_at": "2026-06-22T10:00:00",
  "cost_estimate": 0.003,
  "quality_score": 92.0,
  "governance_status": "pending_review",
  "metadata": {},
  "_manifest_saved_at": "2026-06-22T10:00:01"
}
```

---

## Checksum Verification

All files are SHA-256 hashed on write. The hex digest is stored in
`GeneratedAsset.checksum_sha256` and in the manifest.

To re-verify a file:

```python
from sfc.creative.providers.asset_storage import get_asset_storage

storage = get_asset_storage()
recomputed = storage.compute_checksum("/path/to/file.jpg")
assert recomputed == asset.checksum_sha256
```

---

## File Validation

```python
valid, errors = storage.validate_file("/path/to/file.jpg")
```

Checks:
- File exists on disk
- File size > 0 bytes

---

## Public URL

If `CREATIVE_PUBLIC_BASE_URL` is set, `GeneratedAsset.public_url` is populated:

```
https://cdn.sfc.sa/creative/images/{asset_id}.png
```

If not set, `public_url` is `null`.
