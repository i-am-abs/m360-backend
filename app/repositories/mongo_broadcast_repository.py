from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.interfaces.broadcast_feed_repository import BroadcastFeedRepository

ALLOWED_EMOJIS = ["👍", "❤️", "😂", "🥲", "😊", "🤲"]


class MongoBroadcastFeedRepository(BroadcastFeedRepository):
    def __init__(self, db: Database) -> None:
        self._messages = db["broadcast_messages"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._messages.create_index([("masjid_id", 1), ("created_at", -1)])
        self._messages.create_index([("masjid_id", 1), ("updated_at", -1)])
        self._messages.create_index([("sender.user_id", 1)])

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
        now_iso = self._now_iso()
        doc: Dict[str, Any] = {
            "masjid_id": masjid_id,
            "sender": {
                "user_id": sender["user_id"],
                "name": sender.get("name", ""),
                "role": sender.get("role", ""),
                "avatar_url": sender.get("avatar_url"),
            },
            "message_type": msg_type,
            "text": text,
            "video_url": video_url,
            "campaign_id": campaign_id,
            "thumbnail_url": thumbnail_url,
            "mux_asset_id": mux_asset_id,
            "mux_upload_id": mux_upload_id,
            "mux_playback_id": None,
            "comments": [],
            "reactions": {emoji: [] for emoji in ALLOWED_EMOJIS},
            "reaction_counts": {emoji: 0 for emoji in ALLOWED_EMOJIS},
            "view_count": 0,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        result = self._messages.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._as_dict(doc)

    def get_messages(
        self,
        masjid_id: str,
        cursor: Optional[datetime],
        since: Optional[datetime],
        limit: int,
        user_id: Optional[str] = None,
    ) -> dict:
        query: Dict[str, Any] = {"masjid_id": masjid_id}
        if cursor:
            query["created_at"] = {"$lt": cursor.isoformat()}
        if since:
            query.setdefault("$or", [])
            query["$or"] = [{"updated_at": {"$gt": since.isoformat()}}]
            if cursor:
                query["created_at"] = {"$lt": cursor.isoformat()}

        docs = (
            list(self._messages.find(query).sort("created_at", -1).limit(limit))
        )

        has_more = len(docs) >= limit
        next_cursor = None
        if has_more and docs:
            next_cursor = docs[-1].get("created_at")

        messages = []
        for doc in docs:
            msg = self._as_dict(doc)
            if user_id:
                reactions = doc.get("reactions", {})
                msg["my_reaction"] = next(
                    (e for e, users in reactions.items() if user_id in users),
                    None,
                )
            messages.append(msg)

        return {
            "messages": messages,
            "pagination": {"has_more": has_more, "next_cursor": next_cursor},
        }

    def get_message(self, message_id: str) -> Optional[dict]:
        try:
            doc = self._messages.find_one({"_id": ObjectId(message_id)})
        except Exception:
            return None
        return self._as_dict(doc) if doc else None

    def delete_message(self, message_id: str) -> bool:
        try:
            result = self._messages.delete_one({"_id": ObjectId(message_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> dict:
        doc = self._messages.find_one({"_id": ObjectId(message_id)})
        if not doc:
            return {}

        reactions: Dict[str, List[str]] = doc.get("reactions", {})
        reaction_counts: Dict[str, int] = doc.get("reaction_counts", {})

        for e in ALLOWED_EMOJIS:
            if e not in reactions:
                reactions[e] = []
            if e not in reaction_counts:
                reaction_counts[e] = 0

        if user_id in reactions.get(emoji, []):
            reactions[emoji].remove(user_id)
            reaction_counts[emoji] = max(0, reaction_counts.get(emoji, 0) - 1)
        else:
            for e in ALLOWED_EMOJIS:
                if user_id in reactions.get(e, []):
                    reactions[e].remove(user_id)
                    reaction_counts[e] = max(0, reaction_counts.get(e, 0) - 1)
                    break
            reactions.setdefault(emoji, []).append(user_id)
            reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1

        self._messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "reactions": reactions,
                    "reaction_counts": reaction_counts,
                    "updated_at": self._now_iso(),
                }
            },
        )

        return {
            "reaction_counts": reaction_counts,
            "my_reaction": emoji if user_id in reactions.get(emoji, []) else None,
        }

    def update_mux_playback(
        self,
        asset_id: str,
        playback_id: str,
        video_url: str,
        thumbnail_url: str,
        upload_id: str | None = None,
    ) -> None:
        updates = {
            "mux_playback_id": playback_id,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "updated_at": self._now_iso(),
        }
        result = self._messages.update_one(
            {"mux_asset_id": asset_id},
            {"$set": updates},
        )
        if result.matched_count == 0 and upload_id:
            updates["mux_asset_id"] = asset_id
            self._messages.update_one(
                {"mux_upload_id": upload_id},
                {"$set": updates},
            )

    def increment_view_count(self, message_id: str) -> int:
        try:
            result = self._messages.find_one_and_update(
                {"_id": ObjectId(message_id)},
                {"$inc": {"view_count": 1}},
                return_document=True,
            )
            return result.get("view_count", 0) if result else 0
        except Exception:
            return 0

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _as_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
        doc["id"] = str(doc.pop("_id"))
        return doc
