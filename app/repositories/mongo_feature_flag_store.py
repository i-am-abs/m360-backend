from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.interfaces.feature_flag_repository import FeatureFlagRepository


class MongoFeatureFlagStore(FeatureFlagRepository):
    _COLLECTION = "feature_flag_locations"
    _DEFAULT_KEY = "*"

    def __init__(self, db: Database) -> None:
        self._col = db[self._COLLECTION]
        self._ensure_indexes()
        self._seed_defaults()

    def _ensure_indexes(self) -> None:
        self._col.create_index(
            [("location_key", ASCENDING)],
            unique=True,
            name="location_key_unique",
        )
        self._col.create_index([("priority", DESCENDING)], name="priority_desc")

    def _seed_defaults(self) -> None:
        if self._col.find_one({"location_key": self._DEFAULT_KEY}):
            return
        now = self._now_iso()
        self._col.insert_one({
            "location_key": self._DEFAULT_KEY,
            "country": None,
            "state": None,
            "city": None,
            "bounds": None,
            "features": {
                "verification": True,
                "timings": True,
                "committee_registration": True,
            },
            "priority": 0,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
        })

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_all(self) -> List[Dict[str, Any]]:
        docs = self._col.find({"enabled": True}).sort("priority", DESCENDING)
        return [self._public(doc) for doc in docs]

    def find_by_location_key(self, location_key: str) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one({"location_key": location_key, "enabled": True})
        return self._public(doc) if doc else None

    def find_by_coordinates(
            self,
            latitude: float,
            longitude: float,
    ) -> Optional[Dict[str, Any]]:
        candidates = list(self._col.find({
            "enabled": True,
            "bounds": {"$ne": None},
        }).sort("priority", DESCENDING))
        for doc in candidates:
            bounds = doc.get("bounds") or {}
            if self._point_in_bounds(latitude, longitude, bounds):
                return self._public(doc)
        return None

    def find_by_region(
            self,
            country: Optional[str],
            state: Optional[str],
            city: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        queries = []
        if country and state and city:
            queries.append({"country": country, "state": state, "city": city})
        if country and state:
            queries.append({"country": country, "state": state, "city": None})
        if country:
            queries.append({"country": country, "state": None, "city": None})

        for query in queries:
            doc = self._col.find_one({**query, "enabled": True})
            if doc:
                return self._public(doc)
        return None

    @staticmethod
    def _point_in_bounds(lat: float, lng: float, bounds: Dict[str, Any]) -> bool:
        try:
            return (
                    float(bounds["lat_min"]) <= lat <= float(bounds["lat_max"])
                    and float(bounds["lng_min"]) <= lng <= float(bounds["lng_max"])
            )
        except (KeyError, TypeError, ValueError):
            return False

    @staticmethod
    def _public(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not doc:
            return {}
        result = dict(doc)
        result.pop("_id", None)
        return result


class NoOpFeatureFlagStore(FeatureFlagRepository):
    def list_all(self) -> List[Dict[str, Any]]:
        return []

    def find_by_location_key(self, location_key: str) -> Optional[Dict[str, Any]]:
        return None

    def find_by_coordinates(
            self,
            latitude: float,
            longitude: float,
    ) -> Optional[Dict[str, Any]]:
        return None

    def find_by_region(
            self,
            country: Optional[str],
            state: Optional[str],
            city: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        return None
