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
        self.access_token = None
        self.expiry = None

    def get_access_token(self) -> str:
        if self.access_token and datetime.now() < self.expiry:
            return self.access_token

        try:
            response = requests.post(
                f"{self.config.oauth_url}/oauth2/token",
                data={
                    "grant_type": TokenConfig.GRANT_TYPE.value,
                    "scope": TokenConfig.SCOPE.value,
                },
                auth=(self.config.client_id, self.config.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=SystemConfig.REQUEST_TIMEOUT.value,
            )
            response.raise_for_status()

            body = response.json()
            self.access_token = body["access_token"]

            expires_in = body.get("expires_in", TokenConfig.EXPIRY_TIME.value)
            buffer = TokenConfig.TIME_DELTA.value
            self.expiry = datetime.now() + timedelta(seconds=expires_in - buffer)

            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"OAuth token fetch failed: {e}")
            raise ApiException(f"OAuth token fetch failed: {str(e)}")
        except Exception as e:
            logger.error(f"Token fetch error: {e}")
            raise ApiException(f"OAuth token fetch failed: {str(e)}")
