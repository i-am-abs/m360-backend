from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any, Dict

from constants.env_keys import EnvKeys
from exceptions.api_exception import ApiException
from logger.Logger import Logger
from modules.auth.domain.contracts import OtpGateway, PhoneNumberValidator
from modules.auth.domain.validators import IndiaPhoneNumberValidator
from modules.auth.gateway.msg91_gateway import Msg91OtpGateway
from services.google_places.support.env import load_project_dotenv
from services.user_store import UserStore

logger = Logger.get_logger(__name__)


class PhoneAuthApplicationService:
    def __init__(
        self,
        store: UserStore,
        otp_gateway: OtpGateway | None = None,
        phone_validator: PhoneNumberValidator | None = None,
    ):
        self._store = store
        self._otp_gateway = otp_gateway or Msg91OtpGateway()
        self._phone_validator = phone_validator or IndiaPhoneNumberValidator()

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

    def request_otp(self, phone_number: str) -> Dict[str, Any]:
        formatted_mobile = self._phone_validator.validate_and_format(phone_number)
        data = self._otp_gateway.request_otp(formatted_mobile)
        otp_hint = (
            (data or {}).get("otp")
            or (data or {}).get("code")
            or (data or {}).get("verification_code")
        )
        logger.info(
            "MSG91 OTP requested for %s | request_id=%s | otp=%s | response=%s",
            phone_number,
            (data or {}).get("request_id"),
            otp_hint,
            data,
        )
        return {"phone_number": phone_number, "provider_response": data}

    def verify_otp(self, phone_number: str, otp: str) -> Dict[str, Any]:
        formatted_mobile = self._phone_validator.validate_and_format(phone_number)
        data = self._otp_gateway.verify_otp(formatted_mobile, otp)

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
