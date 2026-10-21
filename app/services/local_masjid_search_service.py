from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.masjid_repository import MasjidEntityRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.utils.masjid import (
    is_google_place_id,
    is_local_masjid_doc,
    masjid_doc_to_place,
    normalize_place_id,
)

_log = get_logger(__name__)


class LocalMasjidSearchService(MasjidSearchService):
    """Merges manually added Mongo masjids into Google Places search/details."""

    def __init__(
            self,
            inner: MasjidSearchService,
            masjid_repo: MasjidEntityRepository,
    ) -> None:
        self._inner = inner
        self._repo = masjid_repo

    def get_place_by_id(self, place_id: str) -> Dict[str, Any]:
        pid = normalize_place_id(place_id)
        if not is_google_place_id(pid):
            place = self._local_place(pid)
            if place:
                return place
            raise ApiException(
                "Place not found",
                status_code=HTTPStatus.NOT_FOUND.value,
                code=ErrorCode.NOT_FOUND,
            )
        try:
            return self._inner.get_place_by_id(pid)
        except ApiException as exc:
            if exc.status_code == HTTPStatus.NOT_FOUND.value:
                place = self._local_place(pid)
                if place:
                    return place
            raise

    def search_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            max_result_count: int,
    ) -> Dict[str, Any]:
        data = self._inner.search_nearby(
            latitude, longitude, radius_meters, max_result_count,
        )
        local = self._local_nearby(latitude, longitude, radius_meters, max_result_count)
        return self._merge(data, local, max_result_count)

    def search_by_name(
            self,
            query: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        data = self._inner.search_by_name(query, max_result_count, radius_meters)
        local = self._local_text(query, max_result_count)
        return self._merge(data, local, max_result_count)

    def search_by_city(
            self,
            city: str,
            max_result_count: int,
            radius_meters: int,
    ) -> Dict[str, Any]:
        data = self._inner.search_by_city(city, max_result_count, radius_meters)
        local = self._local_text(city, max_result_count)
        return self._merge(data, local, max_result_count)

    def _local_place(self, place_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self._repo.get_by_place_id(place_id)
        except Exception as exc:
            _log.warning("Local place lookup failed for %s: %s", place_id, exc)
            return None
        if not doc:
            return None
        return masjid_doc_to_place(doc)

    def _local_text(self, query: str, limit: int) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        try:
            docs = self._repo.search_local_by_text(q, max(1, limit))
        except Exception as exc:
            _log.warning("Local text search failed: %s", exc)
            return []
        return self._to_local_places(docs)

    def _local_nearby(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
            limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            docs = self._repo.search_local_nearby(
                latitude, longitude, radius_meters, max(1, limit),
            )
        except Exception as exc:
            _log.warning("Local nearby search failed: %s", exc)
            return []
        return self._to_local_places(docs)

    @staticmethod
    def _to_local_places(masjids: List[Any]) -> List[Dict[str, Any]]:
        places: List[Dict[str, Any]] = []
        for doc in masjids:
            if not is_local_masjid_doc(doc):
                continue
            place = masjid_doc_to_place(doc)
            if place.get("id"):
                places.append(place)
        return places

    @staticmethod
    def _merge(
            data: Dict[str, Any],
            local_places: List[Dict[str, Any]],
            max_result_count: int,
    ) -> Dict[str, Any]:
        google_places = [
            p for p in (data.get("places") or []) if isinstance(p, dict)
        ]
        seen = {
            normalize_place_id(str(p.get("id") or p.get("place_id") or ""))
            for p in google_places
        }
        extras = []
        for place in local_places:
            pid = normalize_place_id(str(place.get("id") or ""))
            if not pid or pid in seen:
                continue
            seen.add(pid)
            extras.append(place)
        merged = extras + google_places
        cap = max(max_result_count, len(extras))
        data["places"] = merged[:cap]
        return data
