"""Clip Storage Service — uploads rendered video files to Cloudflare R2 or AWS S3.

Activated by setting CLIP_STORAGE_PROVIDER (r2 or s3) plus the matching
credentials. Returns None gracefully when storage is not configured so the
pipeline degrades to local-path-only mode without crashing.

Cloudflare R2 (recommended — free egress):
    CLIP_STORAGE_PROVIDER=r2
    R2_ACCOUNT_ID=<account id>
    R2_ACCESS_KEY_ID=<R2 API token access key>
    R2_SECRET_ACCESS_KEY=<R2 API token secret>
    R2_BUCKET_NAME=<bucket name>
    R2_PUBLIC_URL=https://<bucket>.<account>.r2.dev  (or custom domain)

AWS S3:
    CLIP_STORAGE_PROVIDER=s3
    AWS_ACCESS_KEY_ID=<key>
    AWS_SECRET_ACCESS_KEY=<secret>
    AWS_REGION=<region, e.g. us-east-1>
    S3_BUCKET_NAME=<bucket name>
    S3_PUBLIC_URL=https://<bucket>.s3.<region>.amazonaws.com
"""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path

logger = logging.getLogger("sfc.storage")

_singleton: "ClipStorageService | None" = None


def get_clip_storage_service() -> "ClipStorageService":
    global _singleton
    if _singleton is None:
        _singleton = ClipStorageService()
    return _singleton


class ClipStorageService:
    """Uploads clip files to R2 or S3; returns the public HTTPS URL."""

    def __init__(self) -> None:
        self._provider = os.environ.get("CLIP_STORAGE_PROVIDER", "").lower()
        self._enabled = self._provider in ("r2", "s3")

        if self._provider == "r2":
            self._account_id = os.environ.get("R2_ACCOUNT_ID", "")
            self._access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
            self._secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
            self._bucket = os.environ.get("R2_BUCKET_NAME", "")
            self._public_base = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
            self._endpoint = f"https://{self._account_id}.r2.cloudflarestorage.com"
            self._region = "auto"
            self._enabled = bool(
                self._account_id and self._access_key and self._secret_key and self._bucket
            )
        elif self._provider == "s3":
            self._access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
            self._secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
            self._bucket = os.environ.get("S3_BUCKET_NAME", "")
            self._region = os.environ.get("AWS_REGION", "us-east-1")
            self._public_base = os.environ.get("S3_PUBLIC_URL", "").rstrip("/")
            self._endpoint = None  # boto3 default S3 endpoint
            self._enabled = bool(
                self._access_key and self._secret_key and self._bucket
            )

        if self._enabled:
            logger.info("[Storage] provider=%s bucket=%s", self._provider, self._bucket)
        else:
            logger.debug(
                "[Storage] disabled (CLIP_STORAGE_PROVIDER=%s — credentials not set)",
                self._provider or "unset",
            )

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def upload(self, local_path: str, object_key: str | None = None) -> str | None:
        """Upload ``local_path`` to cloud storage and return the public URL.

        Returns None when storage is disabled or the upload fails — callers
        fall back to local path only.
        """
        if not self._enabled:
            return None

        path = Path(local_path)
        if not path.exists() or not path.is_file():
            logger.warning("[Storage] File not found for upload: %s", local_path)
            return None

        key = object_key or f"clips/{path.name}"
        content_type = mimetypes.guess_type(local_path)[0] or "video/mp4"

        try:
            import boto3
            from botocore.config import Config

            kwargs: dict = dict(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
            )
            if self._endpoint:
                kwargs["endpoint_url"] = self._endpoint

            s3 = boto3.client("s3", **kwargs, config=Config(signature_version="s3v4"))
            s3.upload_file(
                local_path,
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
            )

            public_url = f"{self._public_base}/{key}" if self._public_base else (
                f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
            )
            logger.info("[Storage] Uploaded %s → %s", path.name, public_url)
            return public_url

        except ImportError:
            logger.warning(
                "[Storage] boto3 not installed — cannot upload. "
                "Add boto3 to requirements.txt."
            )
            return None
        except Exception as exc:
            logger.error("[Storage] Upload failed key=%s: %s", key, exc)
            return None
