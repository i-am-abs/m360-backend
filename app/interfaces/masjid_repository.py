from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MasjidRepository(ABC):
    @abstractmethod
    def get_committee(self, place_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def upsert_committee(
            self,
            place_id: str,
            data: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_timings(self, place_id: str) -> Optional[List[Dict[str, Any]]]:
        pass

    @abstractmethod
    def get_amenities(self, place_id: str) -> Optional[List[str]]:
        pass

    @abstractmethod
    def update_timings(
            self,
            place_id: str,
            timings: List[Dict[str, Any]],
            *,
            updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_amenities(
            self,
            place_id: str,
            amenities: List[str],
            *,
            updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_announcements_enabled(self, place_id: str) -> Optional[bool]:
        """Return stored flag, or None when not set."""
        pass

    @abstractmethod
    def set_announcements_enabled(
            self,
            place_id: str,
            enabled: bool,
            *,
            updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass


class MasjidEntityRepository(ABC):
    @abstractmethod
    def upsert_from_google_places(self, place_data: dict) -> dict:
        pass

    @abstractmethod
    def get_by_id(self, masjid_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_by_place_id(self, place_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def search_nearby(self, lat: float, lng: float, radius: int, limit: int, page: int) -> dict:
        pass

    @abstractmethod
    def search_by_city(self, city: str, limit: int, page: int) -> dict:
        pass

    @abstractmethod
    def update_masjid(self, masjid_id: str, updates: dict) -> dict:
        pass

    @abstractmethod
    def update_facilities(self, masjid_id: str, facilities: dict) -> dict:
        pass

    @abstractmethod
    def update_timings(self, masjid_id: str, timings: dict) -> dict:
        pass

    @abstractmethod
    def add_committee_member(self, masjid_id: str, member: dict) -> dict:
        pass

    @abstractmethod
    def remove_committee_member(self, masjid_id: str, user_id: str) -> dict:
        pass

    @abstractmethod
    def list_all(self, skip: int, limit: int) -> dict:
        pass

    @abstractmethod
    def find_by_committee_member(self, user_id: str) -> list:
        pass
