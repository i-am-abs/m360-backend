from __future__ import annotations

from http import HTTPStatus
from typing import List

from app.core.enums.error_code import ErrorCode
from app.core.enums.upload_type import UploadMediaType
from app.exceptions.base import ApiException
from app.interfaces.upload_provider import UploadProvider
from app.schemas.upload import UploadResponse
from app.utils.structured_log import log_event, log_timing


class UploadService:
    _MAX_IMAGE_BYTES = 10 * 1024 * 1024
    _MAX_VIDEO_BYTES = 200 * 1024 * 1024

    def __init__(self, providers: List[UploadProvider]) -> None:
        self._providers = providers

    def upload(
            self,
            file_bytes: bytes,
            filename: str,
            content_type: str,
    ) -> UploadResponse:
        media_type = self._detect_media_type(content_type)
        self._validate_size(media_type, len(file_bytes))

        provider = self._pick_provider(content_type)
        if provider is None:
            raise ApiException(
                f"Unsupported content type: {content_type}",
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.VALIDATION_ERROR,
            )

        with log_timing(
                "upload",
                "upload",
                content_type=content_type,
                size_bytes=len(file_bytes),
        ):
            url = provider.upload(file_bytes, filename, content_type)

        log_event("upload", "completed", content_type=content_type)
        return UploadResponse(url=url)

    def _pick_provider(self, content_type: str) -> UploadProvider | None:
        for provider in self._providers:
            if provider.supports(content_type):
                return provider
        return None

    @staticmethod
    def _detect_media_type(content_type: str) -> UploadMediaType:
        if content_type.lower().startswith("image/"):
            return UploadMediaType.IMAGE
        if content_type.lower().startswith("video/"):
            return UploadMediaType.VIDEO
        raise ApiException(
            "Only image and video uploads are supported",
            status_code=HTTPStatus.BAD_REQUEST.value,
            code=ErrorCode.VALIDATION_ERROR,
        )

    @staticmethod
    def _validate_size(media_type: UploadMediaType, size: int) -> None:
        limit = (
            UploadService._MAX_IMAGE_BYTES
            if media_type == UploadMediaType.IMAGE
            else UploadService._MAX_VIDEO_BYTES
        )
        if size > limit:
            raise ApiException(
                f"File exceeds maximum size of {limit} bytes",
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.VALIDATION_ERROR,
            )
