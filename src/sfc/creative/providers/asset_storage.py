"""LocalAssetStorage — saves generated files with checksums and JSON manifests."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("sfc.creative.providers.storage")

_DEFAULT_STORAGE_ROOT = "./artifacts/creative"

_singleton: "LocalAssetStorage | None" = None


def get_asset_storage(storage_root: str | None = None) -> "LocalAssetStorage":
    global _singleton
    if _singleton is None:
        root = storage_root or os.environ.get(
            "CREATIVE_STORAGE_PATH", _DEFAULT_STORAGE_ROOT
        )
        _singleton = LocalAssetStorage(storage_root=root)
    return _singleton


class LocalAssetStorage:
    """Saves real creative files under a configured root with checksums and manifests."""

    _SUBDIR_MAP = {
        "image": "images",
        "thumbnail": "thumbnails",
        "audio": "audio",
    }

    def __init__(self, storage_root: str = _DEFAULT_STORAGE_ROOT) -> None:
        self._root = Path(storage_root)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for subdir in ("images", "thumbnails", "audio", "manifests"):
            (self._root / subdir).mkdir(parents=True, exist_ok=True)

    def _subdir(self, asset_type: str) -> Path:
        name = self._SUBDIR_MAP.get(asset_type, asset_type)
        return self._root / name

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def save_file(
        self,
        content: bytes,
        asset_id: str,
        asset_type: str,
        extension: str,
    ) -> tuple[str, str, int]:
        """Write content to disk.  Returns (local_path, sha256_hex, file_size)."""
        subdir = self._subdir(asset_type)
        subdir.mkdir(parents=True, exist_ok=True)
        file_path = subdir / f"{asset_id}.{extension}"
        file_path.write_bytes(content)

        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        logger.info(
            "[AssetStorage] Saved | type=%s id=%s size=%d bytes",
            asset_type,
            asset_id[:8],
            file_size,
        )
        return str(file_path), sha256, file_size

    def save_manifest(self, asset_id: str, manifest: dict[str, Any]) -> str:
        """Write manifest JSON alongside the asset. Returns manifest path."""
        manifest_dir = self._root / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"{asset_id}.json"
        manifest["_manifest_saved_at"] = datetime.utcnow().isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
        logger.debug("[AssetStorage] Manifest | id=%s", asset_id[:8])
        return str(manifest_path)

    def validate_file(self, local_path: str) -> tuple[bool, list[str]]:
        """Return (is_valid, errors).  Checks existence and non-zero size."""
        path = Path(local_path)
        errors: list[str] = []
        if not path.exists():
            errors.append(f"File not found: {local_path}")
            return False, errors
        if path.stat().st_size == 0:
            errors.append(f"File is zero bytes: {local_path}")
            return False, errors
        return True, []

    def compute_checksum(self, local_path: str) -> str:
        """Return SHA-256 hex of the file at local_path, or '' if missing."""
        path = Path(local_path)
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @property
    def storage_root(self) -> str:
        return str(self._root)
