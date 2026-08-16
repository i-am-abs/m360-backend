from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from bson import ObjectId

from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidEntityRepository, MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.utils.admin_link import is_user_admin_for_place
from app.utils.amenities import apply_amenity_fields
from app.utils.masjid import normalize_place_id

log = get_logger(__name__)


def _is_valid_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except Exception:
        return False


def _looks_like_place_id(value: str) -> bool:
    return isinstance(value, str) and value.startswith("ChIJ")


class MasjidEntityService:
    def __init__(
        self,
        masjid_repo: MasjidEntityRepository,
        google_places: MasjidSearchService,
        masjid_store: Optional[MasjidRepository] = None,
        admin_store: Optional[AdminRepository] = None,
    ) -> None:
        self._repo = masjid_repo
        self._places = google_places
        self._masjid_store = masjid_store
        self._admin_store = admin_store

    def get_masjid(self, masjid_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        masjid = None
        if _is_valid_object_id(masjid_id):
            masjid = self._repo.get_by_id(masjid_id)
        if masjid is None and _looks_like_place_id(masjid_id):
            masjid = self._repo.get_by_place_id(masjid_id)
        if masjid is None and _looks_like_place_id(masjid_id):
            masjid = self.sync_place_id(masjid_id)
        if masjid is None:
            raise ApiException(
                "Masjid not found",
                status_code=HTTPStatus.NOT_FOUND,
            )

        result = {"masjid": masjid}
        if user_id:
            result["current_user_relationship"] = self._resolve_relationship(user_id, str(masjid["id"]))
        else:
            result["current_user_relationship"] = None
        return result

    def search_nearby(
        self, lat: float, lng: float, radius: int, limit: int, page: int
    ) -> Dict[str, Any]:
        db_result = self._repo.search_nearby(lat, lng, radius, limit, page)
        masjids = db_result.get("masjids", db_result.get("items", []))
        total = db_result.get("pagination", {}).get("total", len(masjids))

        # Only fall back to Google Places if DB is nearly empty (< 5 results)
        if len(masjids) < 5 and len(masjids) < limit:
            try:
                places_result = self._places.search_nearby(lat, lng, radius, limit)
                place_results = places_result.get("places", places_result.get("results", []))
                for place in place_results:
                    place_id = place.get("id") or place.get("place_id")
                    if place_id and not any(
                        m.get("place_id") == place_id or m.get("id") == place_id for m in masjids
                    ):
                        synced = self._repo.upsert_from_google_places(place)
                        masjids.append(synced)
                        total = max(total, len(masjids))
            except Exception as e:
                log.warning("Google Places fallback failed for nearby search: %s", e)

        return {
            "masjids": self._with_amenities(masjids),
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit),
            },
        }

    def search_by_name(self, query: str, limit: int, page: int) -> Dict[str, Any]:
        db_result = self._repo.search_by_city(query, limit, page)
        masjids = db_result.get("masjids", db_result.get("items", []))
        total = db_result.get("pagination", {}).get("total", len(masjids))

        # Only fall back to Google Places if DB is nearly empty
        if len(masjids) < 5 and len(masjids) < limit:
            try:
                places_result = self._places.search_by_name(query, limit, 50000)
                place_results = places_result.get("places", places_result.get("results", []))
                for place in place_results:
                    place_id = place.get("id") or place.get("place_id")
                    if place_id and not any(
                        m.get("place_id") == place_id or m.get("id") == place_id for m in masjids
                    ):
                        synced = self._repo.upsert_from_google_places(place)
                        masjids.append(synced)
                        total = max(total, len(masjids))
            except Exception as e:
                log.warning("Google Places fallback failed for name search: %s", e)

        return {
            "masjids": self._with_amenities(masjids),
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit),
            },
        }

    def update_masjid(self, masjid_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        masjid = self._lookup_masjid(masjid_id)
        if not masjid:
            raise ApiException("Masjid not found", status_code=HTTPStatus.NOT_FOUND)
        committee = masjid.get("management", {}).get("committee", [])
        if not any(m.get("user_id") == user_id for m in committee):
            raise ApiException(
                "Only committee members can update masjid",
                status_code=HTTPStatus.FORBIDDEN,
            )
        return self._repo.update_masjid(str(masjid["id"]), updates)

    def _lookup_masjid(self, masjid_id: str) -> Optional[dict]:
        masjid = None
        if _is_valid_object_id(masjid_id):
            masjid = self._repo.get_by_id(masjid_id)
        if masjid is None and _looks_like_place_id(masjid_id):
            masjid = self._repo.get_by_place_id(masjid_id)
        return masjid

    def update_facilities(self, masjid_id: str, facilities: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        masjid = self._lookup_masjid(masjid_id)
        if not masjid:
            raise ApiException("Masjid not found", status_code=HTTPStatus.NOT_FOUND)
        committee = masjid.get("management", {}).get("committee", [])
        if not any(m.get("user_id") == user_id for m in committee):
            raise ApiException(
                "Only committee members can update facilities",
                status_code=HTTPStatus.FORBIDDEN,
            )
        return self._repo.update_facilities(str(masjid["id"]), facilities)

    def update_timings(
            self,
            masjid_id: str,
            timings: Dict[str, Any],
            user_id: str,
            current_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        masjid = self._lookup_masjid(masjid_id)
        if not masjid:
            raise ApiException("Masjid not found", status_code=HTTPStatus.NOT_FOUND)
        if not self._can_manage_masjid(masjid, user_id, current_user):
            raise ApiException(
                "Only masjid admins can update timings",
                status_code=HTTPStatus.FORBIDDEN,
            )
        return self._repo.update_timings(str(masjid["id"]), timings)

    def add_committee_member(self, masjid_id: str, member_data: Dict[str, Any]) -> Dict[str, Any]:
        masjid = self._repo.get_by_id(masjid_id)
        if not masjid:
            raise ApiException("Masjid not found", status_code=HTTPStatus.NOT_FOUND)
        return self._repo.add_committee_member(masjid_id, member_data)

    def remove_committee_member(self, masjid_id: str, user_id_to_remove: str, actor_user_id: str) -> Dict[str, Any]:
        masjid = self._repo.get_by_id(masjid_id)
        if not masjid:
            raise ApiException("Masjid not found", status_code=HTTPStatus.NOT_FOUND)
        committee = masjid.get("management", {}).get("committee", [])
        if not any(m.get("user_id") == actor_user_id for m in committee):
            raise ApiException(
                "Only committee members can remove members",
                status_code=HTTPStatus.FORBIDDEN,
            )
        return self._repo.remove_committee_member(masjid_id, user_id_to_remove)

    def get_masjid_list(
        self, page: int, limit: int, city: Optional[str] = None, claimed_only: bool = False
    ) -> Dict[str, Any]:
        if city:
            result = self._repo.search_by_city(city, limit, page)
            items = result.get("masjids", result.get("items", []))
            total = result.get("pagination", {}).get("total", result.get("total", len(items)))
        else:
            skip = (page - 1) * limit
            result = self._repo.list_all(skip, limit)
            items = result.get("masjids", [])
            total = result.get("total", len(items))

        if claimed_only:
            items = [m for m in items if m.get("management", {}).get("is_claimed", False)]
            total = len(items)

        return {
            "masjids": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit),
            },
        }

    def list_committee_masjids(self, user_id: str) -> Dict[str, Any]:
        masjids = self._repo.find_by_committee_member(user_id)
        return {"masjids": masjids, "count": len(masjids)}

    def sync_place_id(self, place_id: str) -> Dict[str, Any]:
        existing = self._repo.get_by_place_id(place_id)
        if existing:
            return existing
        place_data = self._places.get_place_by_id(place_id)
        if not place_data:
            raise ApiException(
                "Place not found on Google Places",
                status_code=HTTPStatus.NOT_FOUND,
            )
        return self._repo.upsert_from_google_places(place_data)

    def _with_amenities(self, masjids: list) -> list:
        for masjid in masjids:
            if not isinstance(masjid, dict):
                continue
            pid = normalize_place_id(
                str(masjid.get("place_id") or masjid.get("id") or ""),
            )
            stored = None
            if pid and self._masjid_store is not None:
                stored = self._masjid_store.get_amenities(pid)
            apply_amenity_fields(masjid, stored)
        return masjids

    def _can_manage_masjid(
            self,
            masjid: Dict[str, Any],
            user_id: str,
            current_user: Optional[Dict[str, Any]],
    ) -> bool:
        committee = (masjid.get("management") or {}).get("committee") or []
        if any(m.get("user_id") == user_id for m in committee):
            return True
        place_id = normalize_place_id(str(masjid.get("place_id") or ""))
        actor = current_user or {"user_id": user_id}
        return is_user_admin_for_place(
            place_id,
            current_user=actor,
            admin_store=self._admin_store,
        )

    def _resolve_relationship(self, user_id: str, masjid_id: str) -> str:
        masjid = self._repo.get_by_id(masjid_id)
        if not masjid:
            return "none"
        committee = masjid.get("management", {}).get("committee", [])
        for member in committee:
            if member.get("user_id") == user_id:
                return "committee_member"
        return "none"