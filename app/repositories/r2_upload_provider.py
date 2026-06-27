from __future__ import annotations

import hashlib
import uuid

from app.core.config import Settings
from app.interfaces.upload_provider import UploadProvider
from app.utils.structured_log import log_event


class R2UploadProvider(UploadProvider):
    _IMAGE_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def supports(self, content_type: str) -> bool:
        return content_type.lower() in self._IMAGE_TYPES

    def _s3_client(self):
        if self._client is not None:
            return self._client
        import boto3
        from botocore.config import Config

        self._client = boto3.client(
            "s3",
            endpoint_url=self._settings.r2_endpoint_url,
            aws_access_key_id=self._settings.r2_access_key_id,
            aws_secret_access_key=self._settings.r2_secret_access_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
        return self._client

    def upload(
            self,
            file_bytes: bytes,
            filename: str,
            content_type: str,
    ) -> str:
        if not self._settings.r2_configured:
            raise RuntimeError("R2 upload is not configured")

        key = self._build_key(filename)
        self._s3_client().put_object(
            Bucket=self._settings.r2_bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        url = self._public_url(key)
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

    def _public_url(self, key: str) -> str:
        public_base = (self._settings.r2_public_base_url or "").rstrip("/")
        if public_base:
            return f"{public_base}/{key}"
        endpoint = (self._settings.r2_endpoint_url or "").rstrip("/")
        return f"{endpoint}/{self._settings.r2_bucket_name}/{key}"


class StubR2UploadProvider(UploadProvider):
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
