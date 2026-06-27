from __future__ import annotations

import base64

import httpx

from app.core.config import Settings
from app.interfaces.upload_provider import UploadProvider
from app.utils.structured_log import log_event


class MuxUploadProvider(UploadProvider):
    _VIDEO_TYPES = {
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/mpeg",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def supports(self, content_type: str) -> bool:
        return content_type.lower() in self._VIDEO_TYPES

    def upload(
            self,
            file_bytes: bytes,
            filename: str,
            content_type: str,
    ) -> str:
        if not self._settings.mux_configured:
            raise RuntimeError("Mux upload is not configured")

        upload_id, upload_url = self._create_direct_upload()
        self._put_file(upload_url, file_bytes, content_type)
        playback_url = self._wait_for_playback_url(upload_id)
        log_event(
            "upload.mux",
            "upload_success",
            resource_id=upload_id,
            content_type=content_type,
            size_bytes=len(file_bytes),
        )
        return playback_url

    def _auth_header(self) -> dict[str, str]:
        token_id = self._settings.mux_token_id or ""
        token_secret = self._settings.mux_token_secret or ""
        credentials = base64.b64encode(f"{token_id}:{token_secret}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def _create_direct_upload(self) -> tuple[str, str]:
        url = "https://api.mux.com/video/v1/uploads"
        payload = {
            "new_asset_settings": {"playback_policy": ["public"]},
            "cors_origin": "*",
        }
        with httpx.Client(timeout=self._settings.request_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=self._auth_header())
            response.raise_for_status()
            data = response.json()["data"]
        return data["id"], data["url"]

    def _put_file(self, upload_url: str, body: bytes, content_type: str) -> None:
        with httpx.Client(timeout=60) as client:
            response = client.put(
                upload_url,
                content=body,
                headers={"Content-Type": content_type},
            )
            response.raise_for_status()

    def _wait_for_playback_url(self, upload_id: str) -> str:
        url = f"https://api.mux.com/video/v1/uploads/{upload_id}"
        with httpx.Client(timeout=self._settings.request_timeout_seconds) as client:
            response = client.get(url, headers=self._auth_header())
            response.raise_for_status()
            upload_data = response.json()["data"]
            asset_id = upload_data.get("asset_id")
            if not asset_id:
                return f"https://stream.mux.com/pending/{upload_id}"

            asset_response = client.get(
                f"https://api.mux.com/video/v1/assets/{asset_id}",
                headers=self._auth_header(),
            )
            asset_response.raise_for_status()
            playback_ids = asset_response.json()["data"].get("playback_ids", [])
            if playback_ids:
                return f"https://stream.mux.com/{playback_ids[0]['id']}.m3u8"
        return f"https://stream.mux.com/pending/{upload_id}"


class StubMuxUploadProvider(UploadProvider):
    def supports(self, content_type: str) -> bool:
        return content_type.lower().startswith("video/")

    def upload(
            self,
            file_bytes: bytes,
            filename: str,
            content_type: str,
    ) -> str:
        return f"https://placeholder.mux.local/videos/{filename}"
