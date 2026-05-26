from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.services.user_masjid_service import UserMasjidService


@dataclass(frozen=True)
class MasjidModuleFacade:
    masjidSearchService: MasjidSearchService
    userMasjidService: UserMasjidService
    masjidRepository: Optional[MasjidRepository]
