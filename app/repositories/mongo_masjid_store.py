from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.masjid_repository import MasjidRepository


class MongoMasjidStore(MasjidRepository):
    """MongoDB-backed store for masjid committee, timings, and amenities.

    Collection: ``masjid_committees``

    Document shape::

        {
            "place_id":   str,          # Google Place ID — unique index
            "committee": {
                "name":             str | None,
                "contact_phone":    str | None,
                "contact_email":    str | None,
                "established_year": int | None,
            },
            "timings": [
                {
                    "prayer": "fajr" | "dhuhr" | "asr" | "maghrib" | "isha",
                    "adhan":  "HH:MM",
                    "iqamah": "HH:MM",
                },
                ...
            ],
            "amenities":  list[str],    # values from Amenity enum
            "created_at": str,          # ISO-8601
            "updated_at": str,          # ISO-8601
        }
    """

    _COLLECTION = "masjid_committees"
    _EXCLUDE = {"_id": 0, "place_id": 0}  # fields to strip from public responses

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_indexes(self) -> None:
        self._col.create_index(
            [(("place_id", ASCENDING))],
            unique=True,
            name="place_id_unique",
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # MasjidRepository interface
    # ------------------------------------------------------------------

    def get_committee(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Return committee details for *place_id*, or ``None`` if absent."""
        doc = self._col.find_one({"place_id": place_id}, self._EXCLUDE)
        if not doc:
            return None
        return dict(doc)

    def upsert_committee(
        self,
        place_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create or fully replace the committee document for *place_id*.

        ``created_at`` is preserved on updates; ``updated_at`` is always
        refreshed.
        """
        now = self._now_iso()

        # Merge caller data with timestamps
        payload: Dict[str, Any] = {
            "committee": data.get("committee", {}),
            "timings": data.get("timings", []),
            "amenities": data.get("amenities", []),
            "updated_at": now,
        }

        result = self._col.find_one_and_update(
            {"place_id": place_id},
            [
                {
                    "$set": {
                        **payload,
                        # Preserve created_at if it already exists, else set it now
                        "created_at": {
                            "$ifNull": ["$created_at", now]
                        },
                    }
                }
            ],
            upsert=True,
            return_document=True,  # type: ignore[call-arg]
        )

        stored: Dict[str, Any] = dict(result or {})
        stored.pop("_id", None)
        stored.pop("place_id", None)
        return stored


# ---------------------------------------------------------------------------
# No-op fallback (used when MongoDB is not configured)
# ---------------------------------------------------------------------------

class NoOpMasjidStore(MasjidRepository):
    """In-memory stub that always reports no committee.

    Used when MongoDB is not configured so the rest of the application can
    boot and serve requests without a database connection.
    """

    def get_committee(self, place_id: str) -> Optional[Dict[str, Any]]:
        return None

    def upsert_committee(
        self,
        place_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        # No-op: data is not persisted
        return data
