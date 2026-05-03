from typing import Any, Dict, Protocol


class MasjidPlacesService(Protocol):
    def get_place_by_id(self, place_id: str) -> Dict[str, Any]: ...

    def search_nearby_masjid(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int = 1000,
            max_result_count: int = 10,
    ) -> Dict[str, Any]: ...

    def search_masjid_by_name(
            self,
            query: str,
            max_result_count: int = 10,
            radius_meters: int = 5000,
    ) -> Dict[str, Any]: ...

    def search_masjid_by_city(
            self,
            city: str,
            max_result_count: int = 20,
            radius_meters: int = 5000,
    ) -> Dict[str, Any]: ...
