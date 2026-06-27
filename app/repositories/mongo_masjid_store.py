from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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

    def get_timings(self, place_id: str) -> Optional[List[Dict[str, Any]]]:
        doc = self._col.find_one({"place_id": place_id}, {"timings": 1, "_id": 0})
        if not doc:
            return None
        timings = doc.get("timings")
        return timings if timings else None

    def update_timings(
        self,
        place_id: str,
        timings: List[Dict[str, Any]],
        *,
        updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = self._now_iso()
        update_fields: Dict[str, Any] = {
            "timings": timings,
            "updated_at": now,
        }
        if updated_by:
            update_fields["timings_updated_by"] = updated_by

        result = self._col.find_one_and_update(
            {"place_id": place_id},
            [
                {
                    "$set": {
                        **update_fields,
                        "created_at": {"$ifNull": ["$created_at", now]},
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

    def update_amenities(
        self,
        place_id: str,
        amenities: List[str],
        *,
        updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = self._now_iso()
        update_fields: Dict[str, Any] = {
            "amenities": amenities,
            "updated_at": now,
        }
        if updated_by:
            update_fields["amenities_updated_by"] = updated_by

        result = self._col.find_one_and_update(
            {"place_id": place_id},
            [
                {
                    "$set": {
                        **update_fields,
                        "created_at": {"$ifNull": ["$created_at", now]},
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

    def get_timings(self, place_id: str) -> Optional[List[Dict[str, Any]]]:
        return None

    def update_timings(
        self,
        place_id: str,
        timings: List[Dict[str, Any]],
        *,
        updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {"timings": timings}

    def update_amenities(
        self,
        place_id: str,
        amenities: List[str],
        *,
        updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {"amenities": amenities}
