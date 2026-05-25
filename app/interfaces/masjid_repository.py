from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities.masjid_entity import MasjidEntity


class MasjidRepository(ABC):
    @abstractmethod
    def saveMasjid(self, masjidEntity: MasjidEntity) -> MasjidEntity:
        pass

    @abstractmethod
    def findMasjidByPlaceId(self, placeId: str) -> Optional[MasjidEntity]:
        pass

    @abstractmethod
    def findMasjidsByPlaceIds(self, placeIds: List[str]) -> Dict[str, MasjidEntity]:
        pass

    @abstractmethod
    def upsertFromGooglePlacePayload(self, googlePlacePayload: Dict[str, Any]) -> MasjidEntity:
        pass

    @abstractmethod
    def countMasjids(self) -> int:
        pass
