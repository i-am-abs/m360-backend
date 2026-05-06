from __future__ import annotations

from app.core.config import Settings
from app.interfaces.http_client import HttpClient
from app.interfaces.token_provider import TokenProvider
from app.services.quran.audio_service import AudioService
from app.services.quran.chapter_service import ChapterService
from app.services.quran.juz_service import JuzService
from app.services.quran.verse_service import VerseService


class QuranApiClient:
    def __init__(
            self,
            settings: Settings,
            token_provider: TokenProvider,
            http_client: HttpClient,
    ) -> None:
        self._chapters = ChapterService(settings, token_provider, http_client)
        self._verses = VerseService(settings, token_provider, http_client)
        self._audio = AudioService(settings, token_provider, http_client)
        self._juzs = JuzService(settings, token_provider, http_client)

    @property
    def chapters(self) -> ChapterService:
        return self._chapters

    @property
    def verses(self) -> VerseService:
        return self._verses

    @property
    def audio(self) -> AudioService:
        return self._audio

    @property
    def juzs(self) -> JuzService:
        return self._juzs
