from __future__ import annotations

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.modules.feature_flag.application.ports.feature_flag_repository_port import FeatureFlagRepositoryPort
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity


class MongoFeatureFlagRepository(FeatureFlagRepositoryPort):
    COLLECTION_NAME = "feature_flags"

    def __init__(self, database: Database) -> None:
        self.database = database
        self.featureFlagCollection = database[self.COLLECTION_NAME]
        self.ensureIndexes()

    def ensureIndexes(self) -> None:
        self.featureFlagCollection.create_index(
            [("feature_name", ASCENDING)],
            unique=True,
        )
        self.featureFlagCollection.create_index([("feature_flag_id", ASCENDING)], unique=True)

    def saveFeatureFlag(self, featureFlagEntity: FeatureFlagEntity) -> FeatureFlagEntity:
        payload = featureFlagEntity.toDictionary()
        try:
            self.featureFlagCollection.update_one(
                {"feature_name": featureFlagEntity.featureName},
                {"$set": payload},
                upsert=True,
            )
        except DuplicateKeyError:
            self.featureFlagCollection.replace_one(
                {"feature_name": featureFlagEntity.featureName},
                payload,
                upsert=True,
            )
        return featureFlagEntity

    def findFeatureFlagByName(self, featureName: str) -> Optional[FeatureFlagEntity]:
        document = self.featureFlagCollection.find_one({"feature_name": featureName.strip().upper()})
        if document is None:
            return None
        return FeatureFlagEntity.fromDictionary(document)

    def findAllFeatureFlags(self) -> List[FeatureFlagEntity]:
        documents = self.featureFlagCollection.find({}).sort("feature_name", ASCENDING)
        return [FeatureFlagEntity.fromDictionary(document) for document in documents]

    def deleteFeatureFlagByName(self, featureName: str) -> bool:
        deleteResult = self.featureFlagCollection.delete_one(
            {"feature_name": featureName.strip().upper()}
        )
        return deleteResult.deleted_count > 0

    def countFeatureFlags(self) -> int:
        return self.featureFlagCollection.count_documents({})
