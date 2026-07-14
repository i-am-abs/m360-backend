from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.broadcast_repository import BroadcastRepository
from app.interfaces.follower_repository import FollowerRepository

log = get_logger(__name__)


class BroadcastService:
    def __init__(
        self,
        broadcast_repo: BroadcastRepository,
        follower_repo: FollowerRepository,
        masjid_repo=None,
        fcm_service=None,
    ) -> None:
        self._broadcast_repo = broadcast_repo
        self._follower_repo = follower_repo
        self._masjid_repo = masjid_repo
        self._fcm_service = fcm_service

    def post_message(self, masjid_id: str, sender_info: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        message = self._broadcast_repo.create_message(
            masjid_id=masjid_id,
            sender=sender_info,
            msg_type=data.get("message_type", "text"),
            text=data.get("text"),
            video_url=data.get("video_url"),
            thumbnail_url=data.get("thumbnail_url"),
            mux_asset_id=data.get("mux_asset_id"),
            mux_upload_id=data.get("mux_upload_id"),
            campaign_id=data.get("campaign_id"),
        )
        log.info(
            "Message posted: masjidId=%s sender=%s type=%s",
            masjid_id, sender_info.get("user_id"), data.get("message_type"),
        )

        if self._fcm_service and self._masjid_repo:
            masjid = self._masjid_repo.get_by_id(masjid_id)
            if masjid:
                place_id = masjid.get("place_id") or masjid.get("id", "")
                masjid_name = masjid.get("name", "Masjid")
                self._fcm_service.send_to_topic(
                    topic=f"masjid_{place_id}",
                    title="New Announcement",
                    body=f"New message from {masjid_name}",
                    data={"type": "broadcast", "masjid_id": place_id},
                )

        return message

    def get_message_raw(self, message_id: str) -> Dict[str, Any]:
        msg = self._broadcast_repo.get_message(message_id)
        if not msg:
            raise ApiException("Broadcast not found", status_code=HTTPStatus.NOT_FOUND)
        return msg

    def get_feed(
        self,
        masjid_id: str,
        cursor: Optional[datetime],
        since: Optional[datetime],
        limit: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = self._broadcast_repo.get_messages(masjid_id, cursor, since, limit, user_id=user_id)
        log.info("get_feed: masjid=%s messages=%d", masjid_id, len(result.get("messages", [])))
        campaign_ids = [
            m.get("campaign_id")
            for m in result.get("messages", [])
            if m.get("message_type") == "campaign_card" and m.get("campaign_id")
        ]
        log.info("get_feed: campaign_ids to enrich=%s", campaign_ids)
        if campaign_ids:
            result = self._enrich_with_campaign_data(result, campaign_ids)
        return result

    def _enrich_with_campaign_data(self, feed: Dict[str, Any], campaign_ids: list) -> Dict[str, Any]:
        try:
            from pymongo import MongoClient
            from app.core.config import get_settings
            settings = get_settings()
            client = MongoClient(settings.mongodb_uri)
            db_name = getattr(settings, "mongodb_database", None) or getattr(settings, "mongodb_db_name", None) or "m360"
            db = client[db_name]
            from bson import ObjectId
            obj_ids = []
            for cid in campaign_ids:
                try:
                    obj_ids.append(ObjectId(cid))
                except Exception:
                    pass
            if not obj_ids:
                client.close()
                return feed
            campaigns = {str(c["_id"]): c for c in db.donation_campaigns.find({"_id": {"$in": obj_ids}})}
            for msg in feed.get("messages", []):
                if msg.get("message_type") == "campaign_card" and msg.get("campaign_id"):
                    cid = msg["campaign_id"]
                    if cid in campaigns:
                        c = campaigns[cid]
                        end_date = c.get("end_date")
                        days_left = 0
                        if end_date:
                            try:
                                if isinstance(end_date, str):
                                    ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                                else:
                                    ed = end_date
                                days_left = max(0, (ed - datetime.utcnow()).days)
                            except Exception:
                                pass
                        donors = c.get("donor_count", 0)
                        latest = c.get("latest_donor") or {}
                        msg["campaign"] = {
                            "id": cid,
                            "title": c.get("title", ""),
                            "description": c.get("description"),
                            "target_amount": c.get("target_amount", 0),
                            "raised_amount": c.get("raised_amount", 0),
                            "currency": c.get("currency", "INR"),
                            "donor_count": donors,
                            "days_left": days_left,
                            "latest_donor": latest,
                            "is_active": c.get("is_active", True),
                        }
            client.close()
        except Exception as e:
            log.warning("Failed to enrich campaign data: %s", e)
        return feed

    def delete_message(self, message_id: str, user_id: str) -> bool:
        msg = self._broadcast_repo.get_message(message_id)
        if not msg:
            raise ApiException("Message not found", status_code=HTTPStatus.NOT_FOUND)

        sender = msg.get("sender", {})
        if sender.get("user_id") != user_id:
            raise ApiException(
                "Only the sender can delete this message",
                status_code=HTTPStatus.FORBIDDEN,
            )

        ok = self._broadcast_repo.delete_message(message_id)
        if ok:
            log.info("Message deleted: messageId=%s by userId=%s", message_id, user_id)
        return ok

    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> Dict[str, Any]:
        msg = self._broadcast_repo.get_message(message_id)
        if not msg:
            raise ApiException("Message not found", status_code=HTTPStatus.NOT_FOUND)
        return self._broadcast_repo.toggle_reaction(message_id, user_id, emoji)

    def post_campaign_card(self, masjid_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        message = self._broadcast_repo.create_message(
            masjid_id=masjid_id,
            sender={
                "user_id": "system",
                "name": "System",
                "role": "Campaign",
            },
            msg_type="campaign_card",
            text=None,
            video_url=None,
            thumbnail_url=None,
            mux_asset_id=None,
            mux_upload_id=None,
            campaign_id=campaign_data.get("id"),
        )
        return message

    def handle_mux_asset_ready(self, asset_id: str, playback_id: str, upload_id: Optional[str] = None) -> None:
        self._broadcast_repo.update_mux_playback(
            asset_id=asset_id,
            playback_id=playback_id,
            video_url=f"https://stream.mux.com/{playback_id}.m3u8",
            thumbnail_url=f"https://image.mux.com/{playback_id}/thumbnail.jpg",
            upload_id=upload_id,
        )

    def increment_view_count(self, message_id: str) -> int:
        return self._broadcast_repo.increment_view_count(message_id)