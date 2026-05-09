from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any, Dict, Optional

from httpx import Client, ConnectError, TimeoutException

from app.core.config import Settings, create_ssl_context
from app.core.enums.error_code import ErrorCode
from app.core.enums.msg91 import Msg91Endpoint
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.otp_gateway import OtpGateway

_log = get_logger(__name__)

_MAX_RETRIES = 1
_RETRY_DELAY_S = 1


class Msg91OtpGateway(OtpGateway):
    def __init__(self, settings: Settings) -> None:
        self._widget_token = (settings.msg91_widget_auth_token or "").strip()
        self._widget_id = (settings.msg91_widget_id or "").strip()
        self._timeout = settings.request_timeout_seconds
        self._ssl_ctx = create_ssl_context()

        if not self._widget_token:
            raise ApiException(
                "MSG91 widget token missing. Set MSG91_WIDGET_AUTH_TOKEN.",
                status_code=503,
                code=ErrorCode.CONFIG_MISSING,
            )

        if not self._widget_id:
            raise ApiException(
                "MSG91 widget ID missing. Set MSG91_WIDGET_ID.",
                status_code=503,
                code=ErrorCode.CONFIG_MISSING,
            )
    
    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        payload = {
            "widgetId": self._widget_id,
            "identifier": formatted_mobile,
            "tokenAuth": self._widget_token,
        }

        return self._post(
            endpoint=Msg91Endpoint.SEND_OTP,
            payload=payload,
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def verify_otp(self, req_id: str, otp: str) -> Dict[str, Any]:
        payload = {
            "widgetId": self._widget_id,
            "reqId": req_id,
            "otp": otp,
            "tokenAuth": self._widget_token,
        }

        return self._post(
            endpoint=Msg91Endpoint.VERIFY_OTP,
            payload=payload,
            error_status=HTTPStatus.UNAUTHORIZED.value,
        )

    def retry_otp(self, req_id: str, retry_channel: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "widgetId": self._widget_id,
            "reqId": req_id,
            "tokenAuth": self._widget_token,
        }
        if retry_channel:
            payload["retryChannel"] = retry_channel

        return self._post(
            endpoint=Msg91Endpoint.RETRY_OTP,
            payload=payload,
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": self._widget_token,
        }

    def _post(
        self,
        endpoint: Msg91Endpoint,
        payload: Dict[str, Any],
        error_status: int,
        _attempt: int = 0,
    ) -> Dict[str, Any]:
        try:
            with Client(timeout=self._timeout, verify=self._ssl_ctx) as client:
                response = client.post(
                    endpoint.value,
                    json=payload,
                    headers=self._headers(),
                )
                body = response.json() if response.content else {}
                data: Dict[str, Any] = body if isinstance(body, dict) else {}

        except (ConnectError, TimeoutException) as exc:
            if _attempt < _MAX_RETRIES:
                _log.warning("MSG91 retry: %s", exc)
                time.sleep(_RETRY_DELAY_S)
                return self._post(endpoint, payload, error_status, _attempt + 1)

            raise ApiException(
                "MSG91 unreachable",
                status_code=502,
                code=ErrorCode.MSG91_UNREACHABLE,
            ) from exc

        # HTTP error
        if response.status_code >= 400:
            msg = data.get("message", "MSG91 request failed")
            raise ApiException(
                msg,
                status_code=error_status,
                code=ErrorCode.MSG91_ERROR,
                provider_message=msg,
            )

        if self._is_error(data):
            msg = str(data.get("message") or "MSG91 error")
            code = str(data.get("code", ""))

            if code == "418" or "auth" in msg.lower():
                raise ApiException(
                    "MSG91 authentication failed (418). Check widget token + widgetId.",
                    status_code=401,
                    code=ErrorCode.MSG91_AUTH_FAILED,
                    provider_message=f"{msg} (MSG91 code {code})",
                )

            raise ApiException(
                msg,
                status_code=error_status,
                code=ErrorCode.MSG91_ERROR,
                provider_message=msg,
            )

        return data

    @staticmethod
    def _is_error(data: Dict[str, Any]) -> bool:
        if data.get("hasError") is True:
            return True
        if str(data.get("status", "")).lower() in {"fail", "error", "failed"}:
            return True
        if data.get("errors"):
            return True
        if str(data.get("type", "")).lower() == "error":
            return True
        if data.get("success") is False:
            return True
        return False
