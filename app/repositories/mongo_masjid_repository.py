from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.masjid_repository import MasjidEntityRepository


class MongoMasjidRepository(MasjidEntityRepository):
    def __init__(self, db: Database) -> None:
        self._masjids = db["masjids"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._masjids.create_index([("place_id", ASCENDING)], unique=True, sparse=True)
        self._masjids.create_index([("location", "2dsphere")])
        self._masjids.create_index([("city", ASCENDING), ("meta.status", ASCENDING)])
        self._masjids.create_index([("management.is_claimed", ASCENDING)])
        self._masjids.create_index([("meta.source", ASCENDING)])

    @staticmethod
    def _normalize_place_data(place_data: dict) -> dict:
        normalized = {}
        loc = place_data.get("location", {})
        if isinstance(loc, dict) and "latitude" in loc and "longitude" in loc:
            normalized["lat"] = loc["latitude"]
            normalized["lng"] = loc["longitude"]
        else:
            normalized["lat"] = place_data.get("geometry", {}).get("location", {}).get("lat")
            normalized["lng"] = place_data.get("geometry", {}).get("location", {}).get("lng")

        photos = place_data.get("photos", [])
        photo_urls = []
        # v1 API: photos have "name" with full URL; old API: "photo_reference"
        for p in photos:
            name = p.get("name") or ""
            if name:
                photo_urls.append({"url": name, "width": p.get("width", 0), "height": p.get("height", 0)})

        display_name_raw = place_data.get("displayName", {})
        if isinstance(display_name_raw, dict):
            name = display_name_raw.get("text", place_data.get("name", ""))
        else:
            name = place_data.get("name", "")

        formatted_addr = place_data.get("formattedAddress", place_data.get("formatted_address", ""))
        phone = place_data.get("nationalPhoneNumber", place_data.get("formatted_phone_number", ""))
        website = place_data.get("websiteUri", place_data.get("website", ""))
        maps_uri = place_data.get("googleMapsUri", place_data.get("url", ""))
        rating = place_data.get("rating")
        ratings_total = place_data.get("userRatingCount", place_data.get("user_ratings_total"))
        status = place_data.get("businessStatus", place_data.get("business_status", ""))

        types_raw = place_data.get("types", [])
        types = [t for t in types_raw if isinstance(t, str)]

        normalized["name"] = name
        normalized["formatted_address"] = formatted_addr
        normalized["formatted_phone_number"] = phone
        normalized["website"] = website
        normalized["url"] = maps_uri
        normalized["rating"] = rating
        normalized["user_ratings_total"] = ratings_total
        normalized["business_status"] = status
        normalized["types"] = types
        normalized["photos"] = photo_urls
        return normalized

    def upsert_from_google_places(self, place_data: dict) -> dict:
        place_id = place_data.get("id") or place_data.get("place_id")
        if not place_id:
            raise ValueError("place_id is required")

        n = self._normalize_place_data(place_data)
        lat, lng = n["lat"], n["lng"]
        geo_json = None
        if lat is not None and lng is not None:
            geo_json = {"type": "Point", "coordinates": [float(lng), float(lat)]}

        city = place_data.get("city", "")
        state = place_data.get("state", "")
        country = place_data.get("country", "India")

        # Extract city from formatted address if not provided directly
        if not city and n["formatted_address"]:
            parts = [p.strip() for p in n["formatted_address"].split(",")]
            # Indian addresses: name, area, city, state, pincode
            if len(parts) >= 3:
                city = parts[-3]

        now_iso = self._now_iso()
        google_data = {
            "photos": n["photos"],
            "phone_number": n["formatted_phone_number"],
            "website": n["website"],
            "google_maps_uri": n["url"],
            "rating": n["rating"],
            "user_ratings_total": n["user_ratings_total"],
            "business_status": n["business_status"],
            "utc_offset": place_data.get("utc_offset"),
            "types": n["types"],
            "last_synced_at": now_iso,
        }

        existing = self._masjids.find_one({"place_id": place_id})
        if existing:
            self._masjids.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "google_place_data": google_data,
                        "location": geo_json,
                        "name": n["name"],
                        "address": n["formatted_address"],
                        "city": city or existing.get("city", ""),
                        "state": state or existing.get("state", ""),
                        "country": country or existing.get("country", ""),
                        "meta.updated_at": now_iso,
                        "meta.source": "google_places",
                    }
                },
            )
            return self._as_dict(self._masjids.find_one({"_id": existing["_id"]}))

        doc: Dict[str, Any] = {
            "place_id": place_id,
            "name": n["name"],
            "name_arabic": "",
            "address": n["formatted_address"],
            "city": city,
            "state": state,
            "country": country,
            "postal_code": "",
            "location": geo_json,
            "google_place_data": google_data,
            "facilities": {},
            "services": {},
            "timings": {},
            "contact": {
                "phone": n["formatted_phone_number"],
                "alternate_phone": None,
                "email": None,
                "website": google_data["website"],
                "social": {"facebook": None, "youtube": None, "instagram": None, "telegram": None},
            },
            "management": {"is_claimed": False, "committee": []},
            "meta": {
                "status": "active",
                "source": "google_places",
                "created_at": now_iso,
                "updated_at": now_iso,
            },
        }
        result = self._masjids.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._as_dict(doc)

    def get_by_id(self, masjid_id: str) -> Optional[dict]:
        # Try MongoDB ObjectId first
        try:
            doc = self._masjids.find_one({"_id": ObjectId(masjid_id)})
            if doc:
                return self._as_dict(doc)
        except Exception:
            pass
        # Fallback: masjids synced from Google Places use place_id or id
        doc = self._masjids.find_one({"$or": [{"place_id": masjid_id}, {"id": masjid_id}]})
        return self._as_dict(doc) if doc else None

    def get_by_place_id(self, place_id: str) -> Optional[dict]:
        doc = self._masjids.find_one({"place_id": place_id})
        return self._as_dict(doc) if doc else None

    def find_by_committee_member(self, user_id: str) -> List[Dict[str, Any]]:
        docs = list(self._masjids.find({"management.committee.user_id": user_id}))
        return [self._as_dict(doc) for doc in docs]

    def search_nearby(self, lat: float, lng: float, radius: int, limit: int, page: int) -> dict:
        skip = (page - 1) * limit
        pipeline: List[Dict[str, Any]] = [
            {
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [lng, lat]},
                    "distanceField": "distance_meters",
                    "maxDistance": radius,
                    "spherical": True,
                    "query": {"meta.status": "active"},
                }
            },
            {"$skip": skip},
            {"$limit": limit},
        ]
        items = list(self._masjids.aggregate(pipeline))

        total_pipeline: List[Dict[str, Any]] = [
            {
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [lng, lat]},
                    "distanceField": "distance_meters",
                    "maxDistance": radius,
                    "spherical": True,
                    "query": {"meta.status": "active"},
                }
            },
            {"$count": "total"},
        ]
        count_result = list(self._masjids.aggregate(total_pipeline))
        total = count_result[0]["total"] if count_result else 0

        return {
            "masjids": [self._as_dict(item) for item in items],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, ceil(total / limit)) if total else 1,
            },
        }

    def search_by_city(self, city: str, limit: int, page: int) -> dict:
        skip = (page - 1) * limit
        query = {
            "$or": [
                {"city": {"$regex": city, "$options": "i"}},
                {"address": {"$regex": city, "$options": "i"}},
            ],
            "meta.status": "active",
        }
        total = self._masjids.count_documents(query)
        docs = list(self._masjids.find(query).skip(skip).limit(limit))
        return {
            "masjids": [self._as_dict(doc) for doc in docs],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, ceil(total / limit)) if total else 1,
            },
        }

    def update_masjid(self, masjid_id: str, updates: dict) -> dict:
        set_fields = {}
        for key, value in updates.items():
            if value is not None:
                set_fields[key] = value
        if set_fields:
            set_fields["meta.updated_at"] = self._now_iso()
            self._masjids.update_one({"_id": ObjectId(masjid_id)}, {"$set": set_fields})
        doc = self._masjids.find_one({"_id": ObjectId(masjid_id)})
        return self._as_dict(doc) if doc else {}

    def update_facilities(self, masjid_id: str, facilities: dict) -> dict:
        set_fields = {}
        for key, value in facilities.items():
            if value is not None:
                set_fields[f"facilities.{key}"] = value
        if set_fields:
            set_fields["meta.updated_at"] = self._now_iso()
            self._masjids.update_one({"_id": ObjectId(masjid_id)}, {"$set": set_fields})
        doc = self._masjids.find_one({"_id": ObjectId(masjid_id)})
        return self._as_dict(doc) if doc else {}

    def update_timings(self, masjid_id: str, timings: dict) -> dict:
        set_fields = {}
        for key, value in timings.items():
            if value is not None:
                set_fields[f"timings.{key}"] = value
        if set_fields:
            set_fields["meta.updated_at"] = self._now_iso()
            self._masjids.update_one({"_id": ObjectId(masjid_id)}, {"$set": set_fields})
        doc = self._masjids.find_one({"_id": ObjectId(masjid_id)})
        return self._as_dict(doc) if doc else {}

    def add_committee_member(self, masjid_id: str, member: dict) -> dict:
        member_obj = {
            "user_id": member["user_id"],
            "name": member.get("name", ""),
            "role": member.get("role", "General Member"),
            "phone": member.get("phone"),
            "image": member.get("image"),
        }
        filter_q = (
            {"_id": ObjectId(masjid_id)}
            if ObjectId.is_valid(masjid_id)
            else {"$or": [{"place_id": masjid_id}, {"id": masjid_id}]}
        )
        self._masjids.update_one(
            filter_q,
            {
                "$push": {"management.committee": member_obj},
                "$set": {"management.is_claimed": True, "meta.updated_at": self._now_iso()},
            },
        )
        doc = self._masjids.find_one(filter_q)
        return self._as_dict(doc) if doc else {}

    def remove_committee_member(self, masjid_id: str, user_id: str) -> dict:
        self._masjids.update_one(
            {"_id": ObjectId(masjid_id)},
            {
                "$pull": {"management.committee": {"user_id": user_id}},
                "$set": {"meta.updated_at": self._now_iso()},
            },
        )
        doc = self._masjids.find_one({"_id": ObjectId(masjid_id)})
        return self._as_dict(doc) if doc else {}

    def list_all(self, skip: int, limit: int) -> dict:
        total = self._masjids.count_documents({})
        docs = list(self._masjids.find({}).skip(skip).limit(limit).sort("meta.created_at", -1))
        return {
            "masjids": [self._as_dict(doc) for doc in docs],
            "total": total,
            "page": (skip // limit) + 1,
            "total_pages": max(1, (total + limit - 1) // limit) if total else 1,
        }

    @staticmethod
    def _extract_component(components: List[dict], comp_type: str) -> str:
        for c in components:
            if comp_type in c.get("types", []):
                return c.get("long_name", "")
        return ""

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _as_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
        doc["id"] = str(doc.pop("_id"))
        # Derive flat photo_url for consumers that expect a single string
        if not doc.get("photo_url"):
            photos = doc.get("photos") or []
            if photos:
                doc["photo_url"] = photos[0].get("url")
        return doc