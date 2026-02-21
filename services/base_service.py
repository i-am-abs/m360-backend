from typing import Any, Dict, Optional

from utils.logger import Logger

logger = Logger.get_logger(__name__)


class BaseService:
    def __init__(self, config, token_provider, http_client):
        self.config = config
        self.token_provider = token_provider
        self.http_client = http_client

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        params = params or {}
        try:
            token = self.token_provider.get_access_token()
            headers = {
                "x-auth-token": token,
                "x-client-id": self.config.client_id,
            }
            data = self.http_client.get(
                f"{self.config.base_url}{endpoint}",
                headers=headers,
                params=params,
            )
            return data
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            raise
