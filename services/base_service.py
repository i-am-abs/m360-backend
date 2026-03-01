from exceptions.api_exception import ApiException
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class BaseService:
    def __init__(self, config, token_provider, http_client):
        self.config = config
        self.token_provider = token_provider
        self.http_client = http_client

    def _build_url(self, endpoint: str) -> str:
        # Ensure no double slashes between base_url and endpoint
        base = self.config.base_url.rstrip("/")
        path = endpoint.lstrip("/")
        return f"{base}/{path}"

    def _get(self, endpoint: str, params: dict = None):
        params = params or {}
        url = self._build_url(endpoint)
        headers = {
            "x-auth-token": self.token_provider.get_access_token(),
            "x-client-id": self.config.client_id,
        }
        try:
            return self.http_client.get(url, headers=headers, params=params)
        except ApiException as e:
            if e.status_code == 401:
                logger.warning("401 received for %s — refreshing token and retrying", endpoint)
                self.token_provider.clear_token()
                headers["x-auth-token"] = self.token_provider.get_access_token()
                return self.http_client.get(url, headers=headers, params=params)
            logger.error("Error fetching %s: %s", endpoint, e)
            raise
        except Exception as e:
            logger.error("Unexpected error fetching %s: %s", endpoint, e)
            raise
