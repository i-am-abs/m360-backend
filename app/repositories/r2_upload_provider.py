from __future__ import annotations

import hashlib
import uuid
from http import HTTPStatus

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
        from botocore.exceptions import ClientError

        from app.core.enums.error_code import ErrorCode
        from app.exceptions.base import ApiException

        if not self._settings.r2_configured:
            raise ApiException(
                "R2 upload is not configured",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code=ErrorCode.UPLOAD_NOT_CONFIGURED,
            )

        bucket = self._settings.r2_bucket_name or ""
        key = self._build_key(filename)
        try:
            self._s3_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            provider_msg = exc.response.get("Error", {}).get("Message", str(exc))
            if error_code in {"NoSuchBucket", "NotFound"}:
                raise ApiException(
                    f"R2 bucket '{bucket}' does not exist. Create it in Cloudflare R2 "
                    f"or set R2_BUCKET_NAME to your existing bucket name.",
                    status_code=HTTPStatus.BAD_GATEWAY.value,
                    code=ErrorCode.BAD_GATEWAY,
                    provider_message=provider_msg,
                ) from exc
            if error_code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                raise ApiException(
                    "R2 credentials or permissions are invalid for this bucket.",
                    status_code=HTTPStatus.BAD_GATEWAY.value,
                    code=ErrorCode.BAD_GATEWAY,
                    provider_message=provider_msg,
                ) from exc
            raise ApiException(
                "Image upload to R2 failed.",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code=ErrorCode.BAD_GATEWAY,
                provider_message=provider_msg,
            ) from exc

        url = self._public_url(key)
        log_event(
            "upload.r2",
            "upload_success",
            resource_id=key,
            content_type=content_type,
            size_bytes=len(file_bytes),
            bucket=bucket,
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
