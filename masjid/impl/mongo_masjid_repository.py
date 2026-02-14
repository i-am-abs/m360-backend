from typing import Any, Dict, List

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from masjid.masjid_repository import MasjidRepository


class MongoMasjidRepository(MasjidRepository):
    COLLECTION = "masjids"

    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self._client = MongoClient(mongo_uri)
        self._db: Database = self._client[db_name]
        self._coll: Collection = self._db[self.COLLECTION]
        self._coll.create_index([("location", "2dsphere")])

    def find_nearby(
        self,
        longitude: float,
        latitude: float,
        radius_km: float,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        radius_m = radius_km * 1000
        query = {
            "location": {
                "$geoWithin": {
                    "$centerSphere": [[longitude, latitude], radius_m / 6378100],
                }
            }
        }
        cursor = self._coll.find(query).limit(limit)
        results: List[Dict[str, Any]] = []
        for doc in cursor:
            obj: Dict[str, Any] = dict(doc)
            obj["id"] = str(obj.pop("_id", ""))
            results.append(obj)
        return results
