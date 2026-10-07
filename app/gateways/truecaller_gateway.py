from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any, Dict

from httpx import Client, Limits, Response, Timeout, TransportError

from app.core.config import Settings, create_ssl_context
from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.truecaller_gateway import TruecallerGateway

_log = get_logger(__name__)

_CONNECT_TIMEOUT_S = 3.0
_TOKEN_PATH = "/v1/token"
_USERINFO_PATH = "/v1/userinfo"


class HttpTruecallerGateway(TruecallerGateway):
    def __init__(self, settings: Settings) -> None:
        self._client_id = (settings.truecaller_client_id or "").strip()
        if not self._client_id:
            raise ApiException(
                "Truecaller client ID missing. Set TRUECALLER_CLIENT_ID.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code=ErrorCode.TRUECALLER_NOT_CONFIGURED,
            )
        timeout = float(settings.truecaller_timeout_seconds)
        self._client = Client(
            base_url=settings.truecaller_oauth_base_url,
            timeout=Timeout(timeout, connect=min(_CONNECT_TIMEOUT_S, timeout)),
            verify=create_ssl_context(),
            limits=Limits(max_keepalive_connections=10, keepalive_expiry=60.0),
        )

    def exchange_code(self, authorization_code: str, code_verifier: str) -> str:
        response = self._send(
            "token",
            "POST",
            _TOKEN_PATH,
            data={
                "grant_type": "authorization_code",
                "client_id": self._client_id,
                "code": authorization_code,
                "code_verifier": code_verifier,
            },
        )
        body = self._json(response)
        if response.status_code != HTTPStatus.OK.value or not body.get("access_token"):
            raise ApiException(
                "Truecaller token exchange failed",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.TRUECALLER_AUTH_FAILED,
                provider_message=self._error_message(body, response),
            )
        return str(body["access_token"])

    def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        response = self._send(
            "userinfo",
            "GET",
            _USERINFO_PATH,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = self._json(response)
        if response.status_code != HTTPStatus.OK.value or not body:
            raise ApiException(
                "Could not fetch Truecaller profile",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.TRUECALLER_AUTH_FAILED,
                provider_message=self._error_message(body, response),
            )
        return body

    def _send(self, label: str, method: str, path: str, **kwargs: Any) -> Response:
        started = time.monotonic()
        try:
            response = self._client.request(method, path, **kwargs)
        except TransportError as exc:
            _log.warning("Truecaller %s unreachable: %r", label, exc)
            raise ApiException(
                "Truecaller unreachable",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code=ErrorCode.TRUECALLER_UNREACHABLE,
            ) from exc
        _log.info(
            "Truecaller %s status=%s elapsed_ms=%d",
            label,
            response.status_code,
            (time.monotonic() - started) * 1000,
        )
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

    @staticmethod
    def _error_message(body: Dict[str, Any], response: Response) -> str:
        for key in ("error_description", "message", "error"):
            if body.get(key):
                return str(body[key])
        return f"HTTP {response.status_code}"
