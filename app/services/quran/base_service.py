from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from app.core.config import Settings
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.http_client import HttpClient
from app.interfaces.token_provider import TokenProvider

_log = get_logger(__name__)


class BaseQuranService:
    def __init__(
            self,
            settings: Settings,
            token_provider: TokenProvider,
            http_client: HttpClient,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider
        self._http_client = http_client

    def _build_url(self, endpoint: str) -> str:
        base = self._settings.quran_base_url.rstrip("/")
        return f"{base}/{endpoint.lstrip('/')}"

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "x-auth-token": self._token_provider.get_access_token(),
            "x-client-id": self._settings.quran_client_id or "",
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = self._build_url(endpoint)
        headers = self._auth_headers()
        try:
            return self._http_client.get(url, headers=headers, params=params or {})
        except ApiException as exc:
            if exc.status_code == HTTPStatus.UNAUTHORIZED.value:
                _log.warning("401 for %s — refreshing token", endpoint)
                self._token_provider.clear_token()
                headers = self._auth_headers()
                return self._http_client.get(url, headers=headers, params=params or {})
            raise
