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
        self._auth_key = settings.msg91_auth_key or ""
        self._widget_id = settings.msg91_widget_id or ""
        self._timeout = settings.request_timeout_seconds
        self._ssl_ctx = create_ssl_context()

    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        return self._post(
            endpoint=Msg91Endpoint.SEND_OTP,
            payload={"widgetId": self._widget_id, "identifier": formatted_mobile},
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def retry_otp(
            self,
            widget_id: str,
            req_id: str,
            retry_channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"widgetId": widget_id, "reqId": req_id}
        if retry_channel:
            payload["retryChannel"] = retry_channel
        return self._post(
            endpoint=Msg91Endpoint.RETRY_OTP,
            payload=payload,
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def verify_otp(
            self,
            widget_id: str,
            req_id: str,
            otp: str,
    ) -> Dict[str, Any]:
        return self._post(
            endpoint=Msg91Endpoint.VERIFY_OTP,
            payload={"widgetId": widget_id, "reqId": req_id, "otp": otp},
            error_status=HTTPStatus.UNAUTHORIZED.value,
        )

    def _post(
            self,
            endpoint: Msg91Endpoint,
            payload: Dict[str, Any],
            error_status: int,
            _attempt: int = 0,
    ) -> Dict[str, Any]:
        headers = {
            "authkey": self._auth_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            with Client(timeout=self._timeout, verify=self._ssl_ctx) as client:
                response = client.post(endpoint.value, json=payload, headers=headers)
                data: Dict[str, Any] = response.json() if response.content else {}

        except (ConnectError, TimeoutException) as exc:
            if _attempt < _MAX_RETRIES:
                _log.warning("MSG91 transient error, retrying: %s", exc)
                time.sleep(_RETRY_DELAY_S)
                return self._post(endpoint, payload, error_status, _attempt + 1)
            raise ApiException(
                "MSG91 service unreachable",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code=ErrorCode.MSG91_UNREACHABLE,
            ) from exc

        if response.status_code >= 400:
            msg = (data or {}).get("message", "MSG91 request failed")
            _log.error(
                "MSG91 error | url=%s | status=%s | body=%s",
                endpoint.value, response.status_code, (response.text or "")[:500],
            )
            raise ApiException(
                msg,
                status_code=error_status,
                code=ErrorCode.MSG91_ERROR,
                provider_message=msg,
            )
        return data
