from __future__ import annotations

import json
import time
from http import HTTPStatus
from typing import Any, Dict, Optional, Union

from httpx import Client, ConnectError, TimeoutException

from app.core.config import Settings, create_ssl_context
from app.core.enums.error_code import ErrorCode
from app.core.enums.msg91 import MSG91_RETRY_CHANNEL_CODE, Msg91Endpoint
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.otp_gateway import OtpGateway

_log = get_logger(__name__)

_MAX_RETRIES = 1
_RETRY_DELAY_S = 1


class Msg91OtpGateway(OtpGateway):
    def __init__(self, settings: Settings) -> None:
        self._auth_key = (settings.msg91_auth_key or "").strip()
        self._widget_id = (settings.msg91_widget_id or "").strip()
        self._timeout = settings.request_timeout_seconds
        self._ssl_ctx = create_ssl_context()

        if not self._auth_key:
            raise ApiException(
                "MSG91 auth key missing. Set MSG91_AUTH_KEY.",
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
        }
        _log.info(
            "MSG91 sendOtp request payload=%s",
            {
                "widgetId": self._widget_id,
                "identifier": formatted_mobile,
                "authkey": self._mask_token(self._auth_key),
            },
        )

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
        }

        return self._post(
            endpoint=Msg91Endpoint.VERIFY_OTP,
            payload=payload,
            error_status=HTTPStatus.UNAUTHORIZED.value,
        )

    def retry_otp(self, req_id: str, retry_channel: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "widgetId": self._widget_id,
            "reqId": req_id,
        }
        code = self._msg91_retry_channel_code(retry_channel)
        if code is not None:
            payload["retryChannel"] = code

        return self._post(
            endpoint=Msg91Endpoint.RETRY_OTP,
            payload=payload,
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    @staticmethod
    def _msg91_retry_channel_code(retry_channel: Optional[str]) -> Optional[int]:
        if not retry_channel:
            return None
        raw = str(retry_channel).strip()
        if raw.isdigit():
            return int(raw)
        key = raw.lower()
        return MSG91_RETRY_CHANNEL_CODE.get(key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "authkey": self._auth_key,
        }

    @staticmethod
    def _normalize_response_json(body: Union[None, Dict[str, Any], list, str, Any]) -> Dict[str, Any]:
        if body is None:
            return {}
        if isinstance(body, dict):
            return body
        if isinstance(body, list):
            for item in body:
                if isinstance(item, dict):
                    return item
            return {}
        if isinstance(body, str) and body.strip():
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                return {}
            return Msg91OtpGateway._normalize_response_json(parsed)
        return {}

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
                body_raw = None
                if response.content:
                    try:
                        body_raw = response.json()
                    except ValueError:
                        body_raw = None
                data = self._normalize_response_json(body_raw)
                if endpoint == Msg91Endpoint.SEND_OTP:
                    _log.info(
                        "MSG91 sendOtp response keys=%s",
                        list(data.keys()) if data else [],
                    )

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

        if response.status_code >= 400:
            msg = data.get("message", "MSG91 request failed")
            raise ApiException(
                msg,
                status_code=error_status,
                code=ErrorCode.MSG91_ERROR,
                provider_message=msg,
            )

        if self._is_error(data):
            msg = self._extract_error_message(data)
            code = str(data.get("code", ""))

            if code == "418" or "auth" in msg.lower():
                raise ApiException(
                    "MSG91 authentication failed (418). Check MSG91_AUTH_KEY and widgetId.",
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
        if data.get("hasError"):
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

    @staticmethod
    def _mask_token(token: str) -> str:
        if not token:
            return ""
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    @staticmethod
    def _extract_error_message(data: Dict[str, Any]) -> str:
        if data.get("message"):
            return str(data["message"])
        if data.get("errors"):
            return str(data["errors"])
        status = str(data.get("status", "")).strip()
        code = str(data.get("code", "")).strip()
        if status and code:
            return f"MSG91 {status} (code {code})"
        if status:
            return f"MSG91 {status}"
        return "MSG91 error"
