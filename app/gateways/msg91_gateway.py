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
    """
    MSG91 OTP Widget v5 API.

    Use *either* account Auth Key (header `authkey`) *or* Widget Auth Token
    (header `token` + JSON `tokenAuth`) — see MSG91 OTP → Token help. Do not send
    the widget token as `authkey` or you get 418 AuthenticationFailure.
    """

    def __init__(self, settings: Settings) -> None:
        self._auth_key = (settings.msg91_auth_key or "").strip()
        self._widget_token = (settings.msg91_widget_auth_token or "").strip()
        self._widget_id = (settings.msg91_widget_id or "").strip()
        self._timeout = settings.request_timeout_seconds
        self._ssl_ctx = create_ssl_context()

    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        self._require_widget_credentials()
        payload = {"widgetId": self._widget_id, "identifier": formatted_mobile}
        return self._post(
            endpoint=Msg91Endpoint.SEND_OTP,
            payload=self._with_token_auth(payload),
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def retry_otp(
            self,
            widget_id: str,
            req_id: str,
            retry_channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_api_secret()
        payload: Dict[str, Any] = {"widgetId": widget_id, "reqId": req_id}
        if retry_channel:
            payload["retryChannel"] = retry_channel
        return self._post(
            endpoint=Msg91Endpoint.RETRY_OTP,
            payload=self._with_token_auth(payload),
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def verify_otp(
            self,
            widget_id: str,
            req_id: str,
            otp: str,
    ) -> Dict[str, Any]:
        self._require_api_secret()
        payload = {"widgetId": widget_id, "reqId": req_id, "otp": otp}
        return self._post(
            endpoint=Msg91Endpoint.VERIFY_OTP,
            payload=self._with_token_auth(payload),
            error_status=HTTPStatus.UNAUTHORIZED.value,
        )

    def _with_token_auth(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._widget_token:
            return payload
        return {**payload, "tokenAuth": self._widget_token}

    def _request_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._widget_token:
            headers["token"] = self._widget_token
            return headers
        headers["authkey"] = self._auth_key
        return headers

    def _post(
            self,
            endpoint: Msg91Endpoint,
            payload: Dict[str, Any],
            error_status: int,
            _attempt: int = 0,
    ) -> Dict[str, Any]:
        self._require_api_secret()
        headers = self._request_headers()
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

        self._raise_if_body_error(data, error_status)
        return data

    def _require_api_secret(self) -> None:
        if self._widget_token or self._auth_key:
            if self._widget_token and self._auth_key:
                _log.warning(
                    "MSG91: both MSG91_WIDGET_AUTH_TOKEN and MSG91_AUTH_KEY are set; "
                    "using widget token (token + tokenAuth). Remove one to avoid confusion."
                )
            return
        raise ApiException(
            "MSG91 is not configured — set MSG91_AUTH_KEY (account Auth Key from "
            "OTP Widget → Server-Side Integration → Get Authkey) or "
            "MSG91_WIDGET_AUTH_TOKEN (OTP → Token → generated token for this widget). "
            "If you only have the widget token, use MSG91_WIDGET_AUTH_TOKEN, not MSG91_AUTH_KEY.",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            code=ErrorCode.CONFIG_MISSING,
        )

    def _require_widget_credentials(self) -> None:
        self._require_api_secret()
        if not self._widget_id:
            raise ApiException(
                "MSG91 widget is not configured — set MSG91_WIDGET_ID from your OTP widget setup.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code=ErrorCode.CONFIG_MISSING,
            )

    def _raise_if_body_error(self, data: Dict[str, Any], default_status: int) -> None:
        if not data or not self._msg91_payload_is_error(data):
            return
        msg = str(data.get("message") or "MSG91 request failed")
        code_str = str(data.get("code", "") or "")
        provider_message = msg if not code_str else f"{msg} (MSG91 code {code_str})"

        if (
                code_str == "418"
                or "authenticationfailure" in msg.lower()
                or ("auth" in msg.lower() and "fail" in msg.lower())
        ):
            hint = (
                "If you use the OTP Widget **Token** (from OTP → Token in the panel), "
                "set MSG91_WIDGET_AUTH_TOKEN (not MSG91_AUTH_KEY). "
                "If you use the account **Auth Key** from Server-Side Integration, set MSG91_AUTH_KEY only."
            )
            raise ApiException(
                f"MSG91 authentication failed (418). {hint}",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.MSG91_AUTH_FAILED,
                provider_message=provider_message,
            )

        raise ApiException(
            msg,
            status_code=default_status,
            code=ErrorCode.MSG91_ERROR,
            provider_message=provider_message,
        )

    @staticmethod
    def _msg91_payload_is_error(data: Dict[str, Any]) -> bool:
        t = str(data.get("type", "")).lower()
        if t == "error":
            return True
        if data.get("success") is False:
            return True
        return False
