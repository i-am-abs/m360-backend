from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection

from db.mongo_client import get_database
from db.repository.base_repository import BaseRepository
from logger.Logger import Logger

logger = Logger.get_logger(__name__)


class MasjidRepository(BaseRepository):

    def get_collection(self) -> Collection:
        return get_database()["masjids"]

    def ensure_indexes(self) -> None:
        self.get_collection().create_index("masjid_id", unique=True)
        logger.info("Masjid collection indexes ensured")

    def find_by_masjid_id(self, masjid_id: str) -> Optional[Dict[str, Any]]:
        return self.find_one({"masjid_id": masjid_id})

    def upsert_masjid(self, masjid_id: str, data: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        self.get_collection().update_one(
            {"masjid_id": masjid_id},
            {
                "$set": {**data, "updated_at": now},
                "$setOnInsert": {"masjid_id": masjid_id, "created_at": now},
            },
            upsert=True,
        )

    def get_amenities(self, masjid_id: str) -> List[str]:
        doc = self.find_by_masjid_id(masjid_id)
        if doc is None:
            return []
        return doc.get("amenities", [])

    def set_amenities(self, masjid_id: str, amenities: List[str]) -> None:
        now = datetime.now(timezone.utc)
        self.get_collection().update_one(
            {"masjid_id": masjid_id},
            {
                "$set": {"amenities": amenities, "updated_at": now},
                "$setOnInsert": {"masjid_id": masjid_id, "created_at": now},
            },
            upsert=True,
        )

    def add_amenity(self, masjid_id: str, amenity_key: str) -> None:
        now = datetime.now(timezone.utc)
        self.get_collection().update_one(
            {"masjid_id": masjid_id},
            {
                "$addToSet": {"amenities": amenity_key},
                "$set": {"updated_at": now},
                "$setOnInsert": {"masjid_id": masjid_id, "created_at": now},
            },
            upsert=True,
        )

    def remove_amenity(self, masjid_id: str, amenity_key: str) -> None:
        now = datetime.now(timezone.utc)
        self.get_collection().update_one(
            {"masjid_id": masjid_id},
            {
                "$pull": {"amenities": amenity_key},
                "$set": {"updated_at": now},
            },
        )
