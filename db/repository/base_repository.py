from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection


class BaseRepository(ABC):

    @abstractmethod
    def get_collection(self) -> Collection:
        pass

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.get_collection().find_one(query)

    def find_many(
        self, query: Dict[str, Any], limit: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = self.get_collection().find(query)
        if limit > 0:
            cursor = cursor.limit(limit)
        return list(cursor)

    def insert_one(self, document: Dict[str, Any]) -> Any:
        return self.get_collection().insert_one(document).inserted_id

    def update_one(
        self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False
    ) -> int:
        result = self.get_collection().update_one(query, update, upsert=upsert)
        return result.modified_count

    def delete_one(self, query: Dict[str, Any]) -> int:
        return self.get_collection().delete_one(query).deleted_count
