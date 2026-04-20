import os
from http import HTTPStatus
from typing import Any, Dict, Optional

import requests
from requests import RequestException

from constants.env_keys import EnvKeys
from constants.msg91_config import Msg91Config
from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from services.google_places.support.env import load_project_dotenv


class Msg91OtpGateway:
    """MSG91 Widget OTP Gateway.

    Uses the Widget API v5 (POST / JSON body / authkey header).
    Flow:  send_otp → (optional) retry_otp → verify_otp
    """

    # ------------------------------------------------------------------ #
    #  Config helpers                                                       #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        """Send OTP via the widget API.

        Returns a dict that contains ``reqId``, which the caller MUST
        persist (e.g. in the session) and pass to retry_otp / verify_otp.
        """
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
        """Resend / retry an OTP for an existing request ID."""
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
        """Verify the OTP entered by the user.

        On success MSG91 returns an access token inside the response body.
        """
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

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _post(
        self,
        url: str,
        payload: Dict[str, Any],
        error_status: int,
    ) -> Dict[str, Any]:
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
            raise ApiException(msg, status_code=error_status)
        return data
