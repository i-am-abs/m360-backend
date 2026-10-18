from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.interfaces.truecaller_identity_repository import (
    TruecallerIdentityConflict,
    TruecallerIdentityRepository,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MongoTruecallerIdentityStore(TruecallerIdentityRepository):
    def __init__(self, db: Database) -> None:
        self._identities = db["truecaller_identities"]
        self._identities.create_index([("sub", ASCENDING)], unique=True)
        self._identities.create_index([("user_id", ASCENDING)])

    def find_by_sub(self, sub: str) -> Optional[Dict[str, Any]]:
        return self._identities.find_one({"sub": sub}, {"_id": 0})

    def link(self, sub: str, user_id: str, phone_number: str) -> None:
        now = _now_iso()
        selector = {"sub": sub, "phone_number": phone_number}
        update = {
            "$set": {"user_id": user_id, "last_login_at": now},
            "$setOnInsert": {"linked_at": now},
        }
        try:
            self._identities.update_one(selector, update, upsert=True)
        except DuplicateKeyError:
            # Either a concurrent request inserted the same (sub, phone) first, or
            # `sub` is bound to another phone; only the former matches on retry.
            if self._identities.update_one(selector, update).matched_count == 0:
                raise TruecallerIdentityConflict(sub) from None


class InMemoryTruecallerIdentityStore(TruecallerIdentityRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._by_sub: Dict[str, Dict[str, Any]] = {}

    def find_by_sub(self, sub: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc = self._by_sub.get(sub)
            return dict(doc) if doc else None

    def link(self, sub: str, user_id: str, phone_number: str) -> None:
        now = _now_iso()
        with self._lock:
            doc = self._by_sub.get(sub)
            if doc is None:
                self._by_sub[sub] = {
                    "sub": sub,
                    "phone_number": phone_number,
                    "user_id": user_id,
                    "linked_at": now,
                    "last_login_at": now,
                }
                return
            if doc["phone_number"] != phone_number:
                raise TruecallerIdentityConflict(sub)
            doc.update(user_id=user_id, last_login_at=now)
