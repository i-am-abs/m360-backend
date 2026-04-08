import os
from http import HTTPStatus
from typing import Any, Dict

import requests
from requests import RequestException

from constants.env_keys import EnvKeys
from exceptions.api_exception import ApiException
from services.google_places.support.env import load_project_dotenv
from services.user_store import UserStore


class Msg91PhoneAuthService:
    def __init__(self, store: UserStore):
        self._store = store

    @staticmethod
    def _session_ttl_seconds() -> int:
        load_project_dotenv()
        raw = os.getenv(EnvKeys.AUTH_SESSION_TTL_SECONDS.value, "").strip()
        if not raw:
            raise ApiException(
                "AUTH_SESSION_TTL_SECONDS is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        try:
            return int(raw)
        except ValueError:
            raise ApiException(
                "AUTH_SESSION_TTL_SECONDS must be a valid integer",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )

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

    @staticmethod
    def _country_code() -> str:
        load_project_dotenv()
        value = os.getenv(EnvKeys.MSG91_COUNTRY_CODE.value, "").strip()
        if not value:
            raise ApiException(
                "MSG91_COUNTRY_CODE is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return value

    @staticmethod
    def _request_otp_url() -> str:
        load_project_dotenv()
        value = os.getenv(EnvKeys.MSG91_REQUEST_OTP_URL.value, "").strip()
        if not value:
            raise ApiException(
                "MSG91_REQUEST_OTP_URL is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return value

    @staticmethod
    def _verify_otp_url() -> str:
        load_project_dotenv()
        value = os.getenv(EnvKeys.MSG91_VERIFY_OTP_URL.value, "").strip()
        if not value:
            raise ApiException(
                "MSG91_VERIFY_OTP_URL is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return value

    @staticmethod
    def _request_timeout_seconds() -> int:
        load_project_dotenv()
        raw = os.getenv(EnvKeys.MSG91_REQUEST_TIMEOUT_SECONDS.value, "").strip()
        if not raw:
            raise ApiException(
                "MSG91_REQUEST_TIMEOUT_SECONDS is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        try:
            return int(raw)
        except ValueError:
            raise ApiException(
                "MSG91_REQUEST_TIMEOUT_SECONDS must be a valid integer",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )

    @staticmethod
    def _phone_digits() -> int:
        load_project_dotenv()
        raw = os.getenv(EnvKeys.MSG91_PHONE_DIGITS.value, "").strip()
        if not raw:
            raise ApiException(
                "MSG91_PHONE_DIGITS is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        try:
            return int(raw)
        except ValueError:
            raise ApiException(
                "MSG91_PHONE_DIGITS must be a valid integer",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )

    def _full_mobile(self, phone_number: str) -> str:
        digits = "".join(ch for ch in phone_number if ch.isdigit())
        phone_digits = self._phone_digits()
        if len(digits) < phone_digits:
            raise ApiException(
                "Phone number is invalid",
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        return f"{self._country_code()}{digits[-phone_digits:]}"

    def request_otp(self, phone_number: str) -> Dict[str, Any]:
        params = {
            "mobile": self._full_mobile(phone_number),
            "template_id": self._msg91_template_id(),
            "authkey": self._msg91_auth_key(),
        }
        try:
            response = requests.get(
                self._request_otp_url(),
                params=params,
                timeout=self._request_timeout_seconds(),
            )
            data = response.json() if response.content else {}
        except RequestException as e:
            raise ApiException(
                "MSG91 service unreachable",
                status_code=HTTPStatus.BAD_GATEWAY.value,
            ) from e
        if response.status_code >= 400:
            msg = (data or {}).get("message", "Failed to send OTP")
            raise ApiException(msg, status_code=HTTPStatus.BAD_GATEWAY.value)
        return {"phone_number": phone_number, "provider_response": data}

    def verify_otp(self, phone_number: str, otp: str) -> Dict[str, Any]:
        params = {
            "mobile": self._full_mobile(phone_number),
            "otp": otp,
            "authkey": self._msg91_auth_key(),
        }
        try:
            response = requests.get(
                self._verify_otp_url(),
                params=params,
                timeout=self._request_timeout_seconds(),
            )
            data = response.json() if response.content else {}
        except RequestException as e:
            raise ApiException(
                "MSG91 service unreachable",
                status_code=HTTPStatus.BAD_GATEWAY.value,
            ) from e
        if response.status_code >= 400:
            msg = (data or {}).get("message", "Invalid OTP")
            raise ApiException(msg, status_code=HTTPStatus.UNAUTHORIZED.value)

        msg = str((data or {}).get("message", "")).lower()
        otp_type = str((data or {}).get("type", "")).lower()
        if "success" not in msg and otp_type != "success":
            raise ApiException(
                "OTP verification failed",
                status_code=HTTPStatus.UNAUTHORIZED.value,
            )

        user = self._store.ensure_user(phone_number)
        session = self._store.create_session(
            user_id=user["user_id"],
            ttl_seconds=self._session_ttl_seconds(),
        )
        return {
            "user": user,
            "auth": {
                "access_token": session["access_token"],
                "token_type": "bearer",
                "expires_in": session["expires_in"],
            },
        }
