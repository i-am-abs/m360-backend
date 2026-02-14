import os

from config.quran_api_config import QuranApiConfig
from dotenv import load_dotenv

load_dotenv()


class QuranConfigFactory:
    @classmethod
    def create(cls) -> QuranApiConfig:
        return QuranApiConfig(
            client_id=os.getenv("QURAN_CLIENT_ID", ""),
            client_secret=os.getenv("QURAN_CLIENT_SECRET", ""),
            base_url=os.getenv("QURAN_BASE_URL", "https://api.quran.foundation"),
            oauth_url=os.getenv("QURAN_OAUTH_URL", "https://auth.quran.foundation"),
        )
