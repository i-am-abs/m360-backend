from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any, Dict, Optional

from httpx import Client, Limits, Response, Timeout, TransportError

from app.core.config import Settings, create_ssl_context
from app.core.logging import get_logger
from app.interfaces.truecaller_gateway import (
    TruecallerFailure,
    TruecallerGateway,
    TruecallerGatewayError,
)

_log = get_logger(__name__)

_CONNECT_TIMEOUT_S = 3.0
_TOKEN_PATH = "/v1/token"
_USERINFO_PATH = "/v1/userinfo"


class HttpTruecallerGateway(TruecallerGateway):
    """Truecaller OAuth (PKCE) client.

    Never retries: an authorization code is single-use, so a blind retry after a
    request may have reached Truecaller can only fail or race the first attempt.
    Codes, verifiers and tokens are never logged.
    """

    def __init__(self, settings: Settings, client: Optional[Client] = None) -> None:
        self._client_id = (settings.truecaller_client_id or "").strip()
        if not self._client_id:
            raise ValueError("TRUECALLER_CLIENT_ID is required")
        timeout = float(settings.truecaller_timeout_seconds)
        self._client = client or Client(
            base_url=settings.truecaller_oauth_base_url,
            timeout=Timeout(timeout, connect=min(_CONNECT_TIMEOUT_S, timeout)),
            verify=create_ssl_context(),
            limits=Limits(max_keepalive_connections=10, keepalive_expiry=60.0),
        )

    def exchange_code(self, authorization_code: str, code_verifier: str) -> str:
        response = self._send(
            TruecallerFailure.EXCHANGE,
            "POST",
            _TOKEN_PATH,
            data={
                "grant_type": "authorization_code",
                "client_id": self._client_id,
                "code": authorization_code,
                "code_verifier": code_verifier,
            },
        )
        token = self._json(response).get("access_token")
        if not isinstance(token, str) or not token.strip():
            _log.warning("Truecaller exchange returned no access_token")
            raise TruecallerGatewayError(TruecallerFailure.EXCHANGE)
        return token

    def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        response = self._send(
            TruecallerFailure.PROFILE,
            "GET",
            _USERINFO_PATH,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = self._json(response)
        if not body:
            _log.warning("Truecaller userinfo returned a malformed body")
            raise TruecallerGatewayError(TruecallerFailure.PROFILE)
        return body

    def _send(
            self,
            stage: TruecallerFailure,
            method: str,
            path: str,
            **kwargs: Any,
    ) -> Response:
        started = time.monotonic()
        try:
            response = self._client.request(method, path, **kwargs)
        except TransportError as exc:
            _log.warning("Truecaller %s transport error: %s", stage.value, type(exc).__name__)
            raise TruecallerGatewayError(TruecallerFailure.UNAVAILABLE) from None
        status = response.status_code
        _log.info(
            "Truecaller %s status=%s elapsed_ms=%d",
            stage.value,
            status,
            (time.monotonic() - started) * 1000,
        )
        if status == HTTPStatus.TOO_MANY_REQUESTS.value or status >= 500:
            raise TruecallerGatewayError(TruecallerFailure.UNAVAILABLE)
        if status != HTTPStatus.OK.value:
            _log.warning(
                "Truecaller %s rejected status=%s error=%s",
                stage.value,
                status,
                self._provider_error(response),
            )
            raise TruecallerGatewayError(stage)
        return response

    @staticmethod
    def _json(response: Response) -> Dict[str, Any]:
        if not response.content:
            return {}
        try:
            body = response.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    @classmethod
    def _provider_error(cls, response: Response) -> str:
        error = cls._json(response).get("error")
        return str(error)[:64] if error else "-"
