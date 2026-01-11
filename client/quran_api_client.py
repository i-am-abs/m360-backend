from auth.impl.oauth_token_provider import OAuthTokenProvider
from http_client.impl.requests_http_client import RequestsHttpClient
from services.impl.audio_service import AudioService
from services.impl.chapter_service import ChapterService
from services.impl.hizb_service import HizbService
from services.impl.juz_service import JuzService
from services.impl.manzil_service import ManzilService
from services.impl.resource_service import ResourceService
from services.impl.rub_el_hizb_service import RubElHizbService
from services.impl.ruku_service import RukuService
from services.impl.search_service import SearchService
from services.impl.tafsir_service import TafsirService
from services.impl.translation_service import TranslationService
from services.impl.verse_service import VerseService


class QuranApiClient:

    def __init__(self, config):
        token_provider = OAuthTokenProvider(config)
        http_client = RequestsHttpClient()

        self.chapters = ChapterService(config, token_provider, http_client)
        self.verses = VerseService(config, token_provider, http_client)
        self.resources = ResourceService(config, token_provider, http_client)
        self.search = SearchService(config, token_provider, http_client)
        self.audio = AudioService(config, token_provider, http_client)
        self.juzs = JuzService(config, token_provider, http_client)
        self.translations = TranslationService(config, token_provider, http_client)
        self.tafsirs = TafsirService(config, token_provider, http_client)
        self.hizbs = HizbService(config, token_provider, http_client)
        self.rukus = RukuService(config, token_provider, http_client)
        self.manzils = ManzilService(config, token_provider, http_client)
        self.rub_el_hizbs = RubElHizbService(config, token_provider, http_client)