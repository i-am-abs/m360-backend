import threading
import requests
from datetime import datetime, timedelta
from auth.token_provider import TokenProvider
from constants.system_config import SystemConfig
from constants.token_config import TokenConfig
from exceptions.api_exception import ApiException
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class OAuthTokenProvider(TokenProvider):

    def __init__(self, config):
        self.config = config
        self._access_token = None
        self._expiry = None
        self._lock = threading.Lock()

    def get_access_token(self) -> str:
        if self._access_token and datetime.now() < self._expiry:
            return self._access_token

        with self._lock:
            if self._access_token and datetime.now() < self._expiry:
                return self._access_token
            return self._fetch_token()

    def _fetch_token(self) -> str:
        try:
            response = requests.post(
                f"{self.config.oauth_url}/oauth2/token",
                auth=(self.config.client_id, self.config.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="grant_type=client_credentials&scope=content",
                timeout=SystemConfig.REQUEST_TIMEOUT.value,
            )
            response.raise_for_status()
            body = response.json()
            self._access_token = body["access_token"]
            expires_in = body.get("expires_in", TokenConfig.EXPIRY_TIME.value)
            self._expiry = datetime.now() + timedelta(seconds=expires_in - 30)
            return self._access_token
        except requests.exceptions.ConnectionError as e:
            logger.error("OAuth token fetch connection failed: %s", str(e)[:200])
            raise ApiException(
                "Cannot reach Quran Foundation OAuth (network or DNS failed). "
                "Check internet and QURAN_OAUTH_URL / QF_ENV.",
                status_code=503,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error("OAuth token fetch failed: %s", str(e)[:200])
            raise ApiException(
                "Failed to obtain access token from Quran Foundation OAuth2"
            ) from e
        except Exception as e:
            logger.error("Token fetch error: %s", str(e)[:200])
            raise ApiException(
                "Failed to obtain access token from Quran Foundation OAuth2"
            ) from e

    def clear_token(self) -> None:
        with self._lock:
            self._access_token = None
            self._expiry = None

    @property
    def access_token(self):
        return self._access_token

    @property
    def expiry(self):
        return self._expiry
