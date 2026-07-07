from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.interfaces.donation_repository import DonationRepository


class MongoDonationRepository(DonationRepository):
    def __init__(self, db: Database) -> None:
        self._campaigns = db["donation_campaigns"]
        self._donations = db["donations"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._campaigns.create_index([("masjid_id", 1), ("status", 1)])
        self._campaigns.create_index([("created_by", 1)])
        self._donations.create_index([("campaign_id", 1), ("payment_status", 1), ("created_at", -1)])
        self._donations.create_index([("donor.user_id", 1)])
        self._donations.create_index([("transaction_id", 1)], sparse=True)

    def create_campaign(self, masjid_id: str, created_by: str, data: dict) -> dict:
        now_iso = self._now_iso()
        doc = {
            "masjid_id": masjid_id,
            "created_by": created_by,
            "title": data["title"],
            "description": data.get("description"),
            "target_amount": data["target_amount"],
            "raised_amount": 0,
            "donor_count": 0,
            "start_date": now_iso,
            "end_date": data["end_date"].isoformat() if hasattr(data["end_date"], "isoformat") else data["end_date"],
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        result = self._campaigns.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._as_dict(doc)

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        try:
            doc = self._campaigns.find_one({"_id": ObjectId(campaign_id)})
        except Exception:
            return None
        return self._as_dict(doc) if doc else None

    def get_active_campaigns(self, masjid_id: str) -> List[dict]:
        docs = list(self._campaigns.find({"masjid_id": masjid_id, "status": "active"}).sort("created_at", -1))
        return [self._as_dict(doc) for doc in docs]

    def update_campaign(self, campaign_id: str, updates: dict) -> dict:
        set_fields = {}
        for key, value in updates.items():
            if value is not None:
                if key == "end_date" and hasattr(value, "isoformat"):
                    set_fields[key] = value.isoformat()
                else:
                    set_fields[key] = value
        if set_fields:
            set_fields["updated_at"] = self._now_iso()
            self._campaigns.update_one({"_id": ObjectId(campaign_id)}, {"$set": set_fields})
        doc = self._campaigns.find_one({"_id": ObjectId(campaign_id)})
        return self._as_dict(doc) if doc else {}

    def cancel_campaign(self, campaign_id: str) -> dict:
        self._campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {"status": "cancelled", "updated_at": self._now_iso()}},
        )
        doc = self._campaigns.find_one({"_id": ObjectId(campaign_id)})
        return self._as_dict(doc) if doc else {}

    def create_donation(
        self, campaign_id: str, masjid_id: str, donor: dict, amount: int, payment_method: str
    ) -> dict:
        now_iso = self._now_iso()
        doc = {
            "campaign_id": campaign_id,
            "masjid_id": masjid_id,
            "donor": {"user_id": donor["user_id"], "name": donor.get("name", "")},
            "amount": amount,
            "payment_method": payment_method,
            "payment_status": "pending",
            "transaction_id": None,
            "is_anonymous": donor.get("is_anonymous", False),
            "failure_reason": None,
            "created_at": now_iso,
        }
        result = self._donations.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._as_dict(doc)

    def update_donation_status(
        self, donation_id: str, status: str, transaction_id: Optional[str]
    ) -> dict:
        set_fields: Dict[str, Any] = {"payment_status": status}
        if transaction_id:
            set_fields["transaction_id"] = transaction_id
        self._donations.update_one({"_id": ObjectId(donation_id)}, {"$set": set_fields})
        doc = self._donations.find_one({"_id": ObjectId(donation_id)})
        return self._as_dict(doc) if doc else {}

    def get_donation(self, donation_id: str) -> Optional[dict]:
        try:
            doc = self._donations.find_one({"_id": ObjectId(donation_id)})
        except Exception:
            return None
        return self._as_dict(doc) if doc else None

    def get_campaign_donors(self, campaign_id: str, limit: int) -> List[dict]:
        docs = list(
            self._donations.find({"campaign_id": campaign_id, "payment_status": "completed"})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [self._as_dict(doc) for doc in docs]

    def get_user_donations(self, user_id: str, page: int, limit: int) -> dict:
        skip = (page - 1) * limit
        total = self._donations.count_documents({"donor.user_id": user_id})
        docs = (
            list(self._donations.find({"donor.user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit))
        )
        return {
            "donations": [self._as_dict(doc) for doc in docs],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, ceil(total / limit)) if total else 1,
            },
        }

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _as_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
        doc["id"] = str(doc.pop("_id"))
        return doc