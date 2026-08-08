from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.claim_repository import ClaimRepository


class MongoClaimRepository(ClaimRepository):
    def __init__(self, db: Database) -> None:
        self._claims = db["masjid_claims"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._claims.create_index([("masjid_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
        self._claims.create_index([("status", ASCENDING)])
        self._claims.create_index([("user_id", ASCENDING)])

    def create_claim(self, user_id: str, masjid_id: str, role: str, note: Optional[str]) -> dict:
        doc = {
            "user_id": user_id,
            "masjid_id": masjid_id,
            "claimed_role": role,
            "applicant_note": note,
            "status": "pending",
            "reviewer_id": None,
            "reviewer_note": None,
            "created_at": self._now_iso(),
            "reviewed_at": None,
        }
        result = self._claims.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._as_dict(doc)

    def get_claim(self, claim_id: str) -> Optional[dict]:
        try:
            doc = self._claims.find_one({"_id": ObjectId(claim_id)})
        except Exception:
            return None
        return self._as_dict(doc) if doc else None

    def get_user_claim_for_masjid(self, user_id: str, masjid_id: str) -> Optional[dict]:
        doc = self._claims.find_one({"user_id": user_id, "masjid_id": masjid_id})
        return self._as_dict(doc) if doc else None

    def list_claims(self, status: Optional[str], page: int, limit: int) -> dict:
        skip = (page - 1) * limit
        query: Dict[str, Any] = {}
        if status and status != "all":
            query["status"] = status
        total = self._claims.count_documents(query)
        docs = list(self._claims.find(query).sort("created_at", -1).skip(skip).limit(limit))
        return {
            "claims": [self._as_dict(doc) for doc in docs],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, ceil(total / limit)) if total else 1,
            },
        }

    def approve_claim(self, claim_id: str, reviewer_id: str, note: Optional[str]) -> dict:
        now_iso = self._now_iso()
        self._claims.update_one(
            {"_id": ObjectId(claim_id)},
            {
                "$set": {
                    "status": "approved",
                    "reviewer_id": reviewer_id,
                    "reviewer_note": note,
                    "reviewed_at": now_iso,
                }
            },
        )
        doc = self._claims.find_one({"_id": ObjectId(claim_id)})
        return self._as_dict(doc) if doc else {}

    def reject_claim(self, claim_id: str, reviewer_id: str, note: str) -> dict:
        now_iso = self._now_iso()
        self._claims.update_one(
            {"_id": ObjectId(claim_id)},
            {
                "$set": {
                    "status": "rejected",
                    "reviewer_id": reviewer_id,
                    "reviewer_note": note,
                    "reviewed_at": now_iso,
                }
            },
        )
        doc = self._claims.find_one({"_id": ObjectId(claim_id)})
        return self._as_dict(doc) if doc else {}

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _as_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
        doc["id"] = str(doc.pop("_id"))
        return doc