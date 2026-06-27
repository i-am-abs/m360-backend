from __future__ import annotations

import hashlib
import uuid
from typing import Optional

import httpx

from app.core.config import Settings
from app.interfaces.upload_provider import UploadProvider
from app.utils.structured_log import log_event


class R2UploadProvider(UploadProvider):
    """Upload images to Cloudflare R2 via S3-compatible API."""

    _IMAGE_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def supports(self, content_type: str) -> bool:
        return content_type.lower() in self._IMAGE_TYPES

    def upload(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        if not self._settings.r2_configured:
            raise RuntimeError("R2 upload is not configured")

        key = self._build_key(filename)
        url = self._put_object(key, file_bytes, content_type)
        log_event(
            "upload.r2",
            "upload_success",
            resource_id=key,
            content_type=content_type,
            size_bytes=len(file_bytes),
        )
        return url

    def _build_key(self, filename: str) -> str:
        suffix = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        digest = hashlib.sha256(f"{filename}:{uuid.uuid4()}".encode()).hexdigest()[:16]
        return f"uploads/images/{digest}.{suffix}"

    def _put_object(self, key: str, body: bytes, content_type: str) -> str:
        endpoint = self._settings.r2_endpoint_url.rstrip("/")
        bucket = self._settings.r2_bucket_name
        public_base = (self._settings.r2_public_base_url or "").rstrip("/")
        upload_url = f"{endpoint}/{bucket}/{key}"

        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }
        auth = (self._settings.r2_access_key_id or "", self._settings.r2_secret_access_key or "")

        with httpx.Client(timeout=self._settings.request_timeout_seconds) as client:
            response = client.put(upload_url, content=body, headers=headers, auth=auth)
            response.raise_for_status()

        if public_base:
            return f"{public_base}/{key}"
        return upload_url


class StubR2UploadProvider(UploadProvider):
    """Fallback when R2 is not configured (dev/test)."""

    def supports(self, content_type: str) -> bool:
        return content_type.lower().startswith("image/")

    def upload(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        digest = hashlib.sha256(file_bytes).hexdigest()[:12]
        return f"https://placeholder.r2.local/uploads/{digest}/{filename}"
