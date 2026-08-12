from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class BroadcastFeedRepository(ABC):
    @abstractmethod
    def create_message(
            self,
            masjid_id: str,
            sender: dict,
            msg_type: str,
            text: Optional[str],
            video_url: Optional[str],
            campaign_id: Optional[str],
            thumbnail_url: Optional[str] = None,
            mux_asset_id: Optional[str] = None,
            mux_upload_id: Optional[str] = None,
    ) -> dict:
        pass

    @abstractmethod
    def get_messages(
            self,
            masjid_id: str,
            cursor: Optional[datetime],
            since: Optional[datetime],
            limit: int,
            user_id: Optional[str] = None,
    ) -> dict:
        pass

    @abstractmethod
    def get_message(self, message_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def delete_message(self, message_id: str) -> bool:
        pass

    @abstractmethod
    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> dict:
        pass

    @abstractmethod
    def update_mux_playback(
            self,
            asset_id: str,
            playback_id: str,
            video_url: str,
            thumbnail_url: str,
            upload_id: Optional[str] = None,
    ) -> None:
        pass

    @abstractmethod
    def increment_view_count(self, message_id: str) -> int:
        pass
