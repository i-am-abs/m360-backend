from __future__ import annotations

import threading
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Optional

from httpx import Client, ConnectError, HTTPStatusError

from app.core.config import Settings, create_ssl_context
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.token_provider import TokenProvider

logger = get_logger(__name__)


class OAuthTokenProvider(TokenProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._access_token: Optional[str] = None
        self._expiry: Optional[datetime] = None
        self._lock = threading.Lock()
        self._ssl_ctx = create_ssl_context()

    def get_access_token(self) -> str:
        if self.is_token_valid():
            return self._access_token
        with self._lock:
            if self.is_token_valid():
                return self._access_token
            return self.fetch_token()

    def clear_token(self) -> None:
        with self._lock:
            self._access_token = None
            self._expiry = None

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    @property
    def expiry(self) -> Optional[datetime]:
        return self._expiry

    def is_token_valid(self) -> bool:
        return bool(self._access_token and self._expiry and datetime.now() < self._expiry)

    def fetch_token(self) -> str:
        url = f"{self._settings.quran_oauth_url}/oauth2/token"
        try:
            with Client(
                    timeout=self._settings.request_timeout_seconds,
                    verify=self._ssl_ctx,
            ) as client:
                response = client.post(
                    url,
                    auth=(
                        self._settings.quran_client_id or "",
                        self._settings.quran_client_secret or "",
                    ),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=("grant_type=client_credentials &scope=content"),
                )
                response.raise_for_status()

            body = response.json()
            self._access_token = body["access_token"]
            expires_in = body.get("expires_in", 3600)
            self._expiry = datetime.now() + timedelta(
                seconds=expires_in - 30,
            )
            return self._access_token

        except ConnectError as exc:
            logger.error("OAuth connection failed: %s", str(exc)[:200])
            raise ApiException(
                "Cannot reach Quran Foundation OAuth.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code="OAUTH_UNREACHABLE",
            ) from exc

        except HTTPStatusError as exc:
            logger.error("OAuth HTTP error: %s", str(exc)[:200])
            raise ApiException(
                "Failed to obtain access token.",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code="OAUTH_FAILED",
                provider_message=exc.response.text[:500],
            ) from exc

        except Exception as exc:
            logger.error("OAuth unexpected error: %s", str(exc)[:200])
            raise ApiException(
                "Failed to obtain access token.",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code="OAUTH_FAILED",
            ) from exc
