"""httpx-based HTTP client implementing :class:`HttpClient`.

Uses the **Adapter pattern** — adapts ``httpx.Client`` to the
application's :class:`~app.interfaces.http_client.HttpClient` contract.
"""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any, Dict, Optional

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException

from app.core.config import create_ssl_context
from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.http_client import HttpClient


class HttpxClient(HttpClient):
    def __init__(self, timeout: int = 10, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._ssl_ctx = create_ssl_context()

    def get(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._execute_with_retry(url, headers, params, self._max_retries)

    def _execute_with_retry(
            self,
            url: str,
            headers: Optional[Dict[str, str]],
            params: Optional[Dict[str, Any]],
            retries_left: int,
    ) -> Any:
        try:
            with Client(timeout=self._timeout, verify=self._ssl_ctx) as client:
                response = client.get(url, headers=headers, params=params)
                if response.status_code == HTTPStatus.UNAUTHORIZED.value:
                    raise ApiException(
                        "Unauthorized",
                        status_code=HTTPStatus.UNAUTHORIZED.value,
                        code=ErrorCode.UNAUTHORIZED,
                    )
                response.raise_for_status()
                return response.json()

        except ConnectError as exc:
            raise ApiException(
                "Cannot reach upstream API — check network connectivity.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code=ErrorCode.SERVICE_UNAVAILABLE,
            ) from exc

        except TimeoutException:
            if retries_left > 0:
                time.sleep(1)
                return self._execute_with_retry(url, headers, params, retries_left - 1)
            raise ApiException(
                "Upstream timeout",
                status_code=HTTPStatus.GATEWAY_TIMEOUT.value,
                code=ErrorCode.GATEWAY_TIMEOUT,
            )

        except HTTPStatusError as exc:
            if self._is_transient(exc.response.status_code) and retries_left > 0:
                time.sleep(1)
                return self._execute_with_retry(url, headers, params, retries_left - 1)
            raise ApiException(
                f"Upstream error: {exc.response.status_code}",
                status_code=exc.response.status_code,
                provider_message=exc.response.text[:500],
            ) from exc

    @staticmethod
    def _is_transient(status: int) -> bool:
        return status in (
            HTTPStatus.BAD_GATEWAY.value,
            HTTPStatus.SERVICE_UNAVAILABLE.value,
        )
