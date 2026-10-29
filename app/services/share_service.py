from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from app.core.config import Settings
from app.exceptions.base import ApiException
from app.interfaces.share_repository import ShareRepository
from app.utils.broadcast import resolve_share_state


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


class ShareService:
    def __init__(
        self,
        share_repo: ShareRepository,
        feed_service,
        settings: Settings,
        masjid_repo=None,
    ) -> None:
        self._repo = share_repo
        self._feed = feed_service
        self._settings = settings
        self._masjid_repo = masjid_repo

    def get_share(self, share_id: str) -> Optional[Dict[str, Any]]:
        if not share_id:
            return None
        return self._repo.get_by_share_id(share_id)

    def create_share(
        self,
        *,
        message_id: str,
        channel: str,
        platform: str,
        parent_share_id: Optional[str] = None,
        user_id: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
    ) -> Dict[str, Any]:
        message = self._feed.get_message_raw(message_id)
        if resolve_share_state(message) != "available":
            raise ApiException(
                "This announcement can no longer be shared",
                status_code=HTTPStatus.CONFLICT,
            )

        parent_share_id = parent_share_id or None
        parent = None
        if parent_share_id:
            parent = self._repo.get_by_share_id(parent_share_id)
            if parent is None:
                raise ApiException("Share link not found", status_code=HTTPStatus.NOT_FOUND)
            if str(parent.get("message_id")) != str(message_id):
                raise ApiException(
                    "Share link does not belong to this announcement",
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

        share_id = str(uuid.uuid4())
        root_share_id = (parent or {}).get("root_share_id") or share_id

        masjid_id = str(message.get("masjid_id") or "")
        masjid_name = str(message.get("masjid_name") or "")
        if masjid_id and self._masjid_repo is not None:
            masjid = self._masjid_repo.get_by_id(masjid_id)
            if masjid and masjid.get("name"):
                masjid_name = str(masjid["name"])

        record = {
            "share_id": share_id,
            "message_id": str(message_id),
            "masjid_id": masjid_id,
            "masjid_name": masjid_name,
            "video_id": str(message_id),
            "mux_playback_id": message.get("mux_playback_id"),
            "root_share_id": root_share_id,
            "parent_share_id": parent_share_id,
            "created_by_user_id": user_id,
            "channel": channel,
            "platform": platform,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "created_at": _now_iso(),
        }
        self._repo.create(record)
        record["url"] = self._build_url(
            message_id, share_id, utm_source, utm_medium, utm_campaign
        )
        return record

    def _build_url(
        self,
        message_id: str,
        share_id: str,
        utm_source: Optional[str],
        utm_medium: Optional[str],
        utm_campaign: Optional[str],
    ) -> str:
        base = self._settings.share_web_base_url.rstrip("/")
        params: Dict[str, str] = {"share": share_id}
        if utm_source:
            params["utm_source"] = utm_source
        if utm_medium:
            params["utm_medium"] = utm_medium
        if utm_campaign:
            params["utm_campaign"] = utm_campaign
        return f"{base}/s/{message_id}?{urlencode(params)}"
