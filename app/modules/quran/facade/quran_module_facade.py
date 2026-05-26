from __future__ import annotations

from dataclasses import dataclass

from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService


@dataclass(frozen=True)
class QuranModuleFacade:
    quranApiClient: QuranApiClient
    quranOAuthService: QuranOAuthService
