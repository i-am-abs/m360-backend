from typing import Any, Dict, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from core.auth.user_repository import UserRepository


class MongoUserRepository(UserRepository):
    COLLECTION = "users"

    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self._client = MongoClient(mongo_uri)
        self._db: Database = self._client[db_name]
        self._coll: Collection = self._db[self.COLLECTION]
        self._coll.create_index("username", unique=True)

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        doc = self._coll.find_one({"username": username})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    def create_user(
            self,
            username: str,
            hashed_password: str,
            email: Optional[str] = None,
    ) -> Dict[str, Any]:
        doc = {
            "username": username,
            "hashed_password": hashed_password,
            "email": email,
        }
        try:
            result = self._coll.insert_one(doc)
            doc["id"] = str(result.inserted_id)
            doc.pop("_id", None)
            return doc
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise ValueError(f"Username '{username}' already exists") from e
            raise
