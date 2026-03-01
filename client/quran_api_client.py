from auth.token_singleton import get_token_provider
from http_client.impl.requests_http_client import RequestsHttpClient
from services.impl.audio_service import AudioService
from services.impl.chapter_service import ChapterService
from services.impl.juz_service import JuzService
from services.impl.verse_service import VerseService


class QuranApiClient:

    def __init__(self, config):
        token_provider = get_token_provider(config)
        http_client = RequestsHttpClient()

        self.chapters = ChapterService(config, token_provider, http_client)
        self.verses = VerseService(config, token_provider, http_client)
        self.audio = AudioService(config, token_provider, http_client)
        self.juzs = JuzService(config, token_provider, http_client)
