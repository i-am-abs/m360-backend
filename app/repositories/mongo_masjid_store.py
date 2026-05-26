from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, GEOSPHERE
from pymongo.database import Database

from app.domain.entities.masjid_entity import MasjidEntity
from app.interfaces.masjid_repository import MasjidRepository


class MongoMasjidStore(MasjidRepository):
    COLLECTION_NAME = "masjids"

    def __init__(self, database: Database) -> None:
        self.database = database
        self.masjidsCollection = database[self.COLLECTION_NAME]
        self.ensureIndexes()

    def ensureIndexes(self) -> None:
        self.masjidsCollection.create_index([("place_id", ASCENDING)], unique=True)
        self.masjidsCollection.create_index([("last_fetched_at", ASCENDING)])
        self.masjidsCollection.create_index([("location", GEOSPHERE)])

    def saveMasjid(self, masjidEntity: MasjidEntity) -> MasjidEntity:
        payload = masjidEntity.toDictionary()
        payload["location"] = self.buildGeoJsonPoint(masjidEntity)
        self.masjidsCollection.update_one(
            {"place_id": masjidEntity.placeId},
            {"$set": payload},
            upsert=True,
        )
        return masjidEntity

    def findMasjidByPlaceId(self, placeId: str) -> Optional[MasjidEntity]:
        document = self.masjidsCollection.find_one({"place_id": placeId.strip()})
        if document is None:
            return None
        return MasjidEntity.fromDictionary(document)

    def findMasjidsByPlaceIds(self, placeIds: List[str]) -> Dict[str, MasjidEntity]:
        normalizedPlaceIds = [placeId.strip() for placeId in placeIds if placeId and placeId.strip()]
        if not normalizedPlaceIds:
            return {}
        documents = self.masjidsCollection.find({"place_id": {"$in": normalizedPlaceIds}})
        return {
            str(document["place_id"]): MasjidEntity.fromDictionary(document)
            for document in documents
        }

    def upsertFromGooglePlacePayload(self, googlePlacePayload: Dict[str, Any]) -> MasjidEntity:
        masjidEntity = MasjidEntity.fromGooglePlacePayload(googlePlacePayload)
        existingMasjid = self.findMasjidByPlaceId(masjidEntity.placeId)
        if existingMasjid is not None:
            masjidEntity.createdAt = existingMasjid.createdAt
        masjidEntity.updatedAt = datetime.now(timezone.utc)
        masjidEntity.lastFetchedAt = masjidEntity.updatedAt
        return self.saveMasjid(masjidEntity)

    def countMasjids(self) -> int:
        return self.masjidsCollection.count_documents({})

    def buildGeoJsonPoint(self, masjidEntity: MasjidEntity) -> Optional[Dict[str, Any]]:
        latitude = masjidEntity.extractLatitude()
        longitude = masjidEntity.extractLongitude()
        if latitude is None or longitude is None:
            return None
        return {
            "type": "Point",
            "coordinates": [longitude, latitude],
        }
