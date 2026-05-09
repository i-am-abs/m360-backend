from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.otp_gateway import OtpGateway
from app.interfaces.phone_validator import PhoneValidator
from app.interfaces.user_repository import UserRepository

_log = get_logger(__name__)


class PhoneAuthService:
    def __init__(
            self,
            store: UserRepository,
            otp_gateway: OtpGateway,
            phone_validator: PhoneValidator,
            session_ttl_seconds: int,
    ) -> None:
        self._store = store
        self._otp_gateway = otp_gateway
        self._phone_validator = phone_validator
        self._session_ttl = session_ttl_seconds

    def request_otp(self, phone_number: str) -> Dict[str, Any]:
        formatted = self._phone_validator.validate_and_format(phone_number)
        data = self._otp_gateway.send_otp(formatted)
        req_id = self._extract_req_id(data)
        if not req_id:
            raise ApiException(
                "OTP provider did not return request ID",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code=ErrorCode.MSG91_ERROR,
                provider_message=str(data.get("errors") or data.get("message") or data),
            )
        _log.info("OTP sent for %s | reqId=%s", phone_number, req_id)
        return {"phone_number": phone_number, "req_id": req_id, "provider_response": data}

    def retry_otp(
            self,
            phone_number: str,
            req_id: str,
            retry_channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self._otp_gateway.retry_otp(req_id, retry_channel)
        _log.info("OTP retry for %s | reqId=%s | channel=%s", phone_number, req_id, retry_channel)
        return {"phone_number": phone_number, "req_id": req_id, "provider_response": data}

    def verify_otp(self, phone_number: str, req_id: str, otp: str) -> Dict[str, Any]:
        self._phone_validator.validate_and_format(phone_number)
        data = self._otp_gateway.verify_otp(req_id, otp)
        self._assert_verification_success(data)
        user = self._store.ensure_user(phone_number)
        session = self._store.create_session(user["user_id"], self._session_ttl)
        _log.info("OTP verified for %s | userId=%s", phone_number, user["user_id"])
        return {
            "user": user,
            "auth": {
                "access_token": session["access_token"],
                "token_type": "bearer",
                "expires_in": session["expires_in"],
            },
        }

    @staticmethod
    def _extract_req_id(data: Dict[str, Any]) -> Optional[str]:
        return (
            (data or {}).get("reqId")
            or (data or {}).get("request_id")
            or (data or {}).get("req_id")
        )

    @staticmethod
    def _assert_verification_success(data: Dict[str, Any]) -> None:
        msg = str((data or {}).get("message", "")).lower()
        otp_type = str((data or {}).get("type", "")).lower()
        if "success" not in msg and otp_type != "success":
            raise ApiException(
                "OTP verification failed",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.OTP_INVALID,
                provider_message=(data or {}).get("message"),
            )
