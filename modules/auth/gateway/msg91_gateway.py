import os
from http import HTTPStatus
from typing import Any, Dict

import requests
from requests import RequestException

from constants.env_keys import EnvKeys
from constants.msg91_config import Msg91Config
from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from services.google_places.support.env import load_project_dotenv


class Msg91OtpGateway:
    @staticmethod
    def _msg91_auth_key() -> str:
        load_project_dotenv()
        key = os.getenv(EnvKeys.MSG91_AUTH_KEY.value, "").strip()
        if not key:
            raise ApiException(
                "MSG91 auth key is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return key

    @staticmethod
    def _msg91_template_id() -> str:
        load_project_dotenv()
        template_id = os.getenv(EnvKeys.MSG91_TEMPLATE_ID.value, "").strip()
        if not template_id:
            raise ApiException(
                "MSG91 template id is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return template_id

    def request_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        params = {
            "mobile": formatted_mobile,
            "template_id": self._msg91_template_id(),
            "authkey": self._msg91_auth_key(),
        }
        return self._call_msg91(params=params, error_status=HTTPStatus.BAD_GATEWAY.value)

    def verify_otp(self, formatted_mobile: str, otp: str) -> Dict[str, Any]:
        params = {
            "mobile": formatted_mobile,
            "otp": otp,
            "authkey": self._msg91_auth_key(),
        }
        return self._call_msg91(
            params=params,
            error_status=HTTPStatus.UNAUTHORIZED.value,
        )

    @staticmethod
    def _call_msg91(params: Dict[str, Any], error_status: int) -> Dict[str, Any]:
        try:
            response = requests.get(
                Msg91Config.OTP_SEND_URL.value,
                params=params,
                timeout=SystemConfig.REQUEST_TIMEOUT.value,
            )
            data = response.json() if response.content else {}
        except RequestException as e:
            raise ApiException(
                "MSG91 service unreachable",
                status_code=HTTPStatus.BAD_GATEWAY.value,
            ) from e

        if response.status_code >= 400:
            msg = (data or {}).get("message", "MSG91 OTP request failed")
            raise ApiException(msg, status_code=error_status)
        return data
