import os
from http import HTTPStatus
from typing import Any, Dict, Optional

import requests
from requests import RequestException

from constants.env_keys import EnvKeys
from constants.msg91_config import Msg91Config
from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from logger.Logger import Logger
from services.google_places.support.env import load_project_dotenv

logger = Logger.get_logger(__name__)


class Msg91OtpGateway:
    @staticmethod
    def _auth_key() -> str:
        load_project_dotenv()
        key = os.getenv(EnvKeys.MSG91_AUTH_KEY.value, "").strip()
        if not key:
            raise ApiException(
                "MSG91_AUTH_KEY is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return key

    @staticmethod
    def _widget_id() -> str:
        load_project_dotenv()
        widget_id = os.getenv(EnvKeys.MSG91_WIDGET_ID.value, "").strip()
        if not widget_id:
            raise ApiException(
                "MSG91_WIDGET_ID is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return widget_id

    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        payload = {
            "widgetId": self._widget_id(),
            "identifier": formatted_mobile,
        }
        return self._post(
            url=Msg91Config.WIDGET_SEND_OTP_URL.value,
            payload=payload,
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def retry_otp(
            self,
            widget_id: str,
            req_id: str,
            retry_channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "widgetId": widget_id,
            "reqId": req_id,
        }
        if retry_channel:
            payload["retryChannel"] = retry_channel
        return self._post(
            url=Msg91Config.WIDGET_RETRY_OTP_URL.value,
            payload=payload,
            error_status=HTTPStatus.BAD_GATEWAY.value,
        )

    def verify_otp(
            self,
            widget_id: str,
            req_id: str,
            otp: str,
    ) -> Dict[str, Any]:
        payload = {
            "widgetId": widget_id,
            "reqId": req_id,
            "otp": otp,
        }
        return self._post(
            url=Msg91Config.WIDGET_VERIFY_OTP_URL.value,
            payload=payload,
            error_status=HTTPStatus.UNAUTHORIZED.value,
        )

    def _post(
            self,
            url: str,
            payload: Dict[str, Any],
            error_status: int,
    ) -> Dict[str, Any]:
        # def _mask(value: Any, keep: int = 3) -> str:
        #     raw = str(value or "")
        #     if not raw:
        #         return ""
        #     if len(raw) <= keep * 2:
        #         return "*" * len(raw)
        #     return f"{raw[:keep]}{'*' * (len(raw) - (keep * 2))}{raw[-keep:]}"

        diagnostic_payload = {
            "widgetId": payload.get("widgetId"),
            "identifier": payload.get("identifier"),
            "reqId": payload.get("reqId"),
            "retryChannel": payload.get("retryChannel"),
        }
        headers = {
            "authkey": self._auth_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=SystemConfig.REQUEST_TIMEOUT.value,
            )
            data: Dict[str, Any] = response.json() if response.content else {}
        except RequestException as exc:
            raise ApiException(
                "MSG91 service unreachable",
                status_code=HTTPStatus.BAD_GATEWAY.value,
            ) from exc

        if response.status_code >= 400:
            msg = (data or {}).get("message", "MSG91 request failed")
            body_preview = (response.text or "")[:500]
            logger.error(
                "MSG91 request failed | url=%s | status=%s | payload=%s | response=%s",
                url,
                response.status_code,
                diagnostic_payload,
                body_preview,
            )
            raise ApiException(msg, status_code=error_status)
        return data
