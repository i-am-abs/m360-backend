from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.integrations.msg91_pending_req import Msg91PendingReqIdStore
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
            msg91_pending: Optional[Msg91PendingReqIdStore] = None,
            msg91_async_req_id_wait_seconds: float = 0.0,
    ) -> None:
        self._store = store
        self._otp_gateway = otp_gateway
        self._phone_validator = phone_validator
        self._session_ttl = session_ttl_seconds
        self._msg91_pending = msg91_pending
        self._msg91_async_wait = msg91_async_req_id_wait_seconds

    def request_otp(self, phone_number: str) -> Dict[str, Any]:
        formatted = self._phone_validator.validate_and_format(phone_number)
        if self._msg91_pending is not None:
            self._msg91_pending.discard_identifier(formatted)
        data = self._otp_gateway.send_otp(formatted)
        req_id = self._extract_req_id(data)
        if (
                not req_id
                and self._msg91_pending is not None
                and self._msg91_async_wait > 0
        ):
            req_id = self._msg91_pending.wait_for(
                formatted,
                total_seconds=self._msg91_async_wait,
                interval=0.2,
            )
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
        """Parse MSG91 (and similar) sendOtp payloads — widget API often uses `message` for the id."""
        if data is None or not isinstance(data, dict):
            return None
        nested_raw = data.get("data")
        nested_dict = nested_raw if isinstance(nested_raw, dict) else None

        layers: list[Dict[str, Any]] = [data]
        if nested_dict is not None:
            layers.append(nested_dict)
        for extra_key in ("response", "result"):
            block = data.get(extra_key)
            if isinstance(block, dict):
                layers.append(block)

        for layer in layers:
            for key in ("reqId", "request_id", "req_id", "requestId"):
                val = layer.get(key)
                if val is not None and str(val).strip():
                    return str(val).strip()

        deep = PhoneAuthService._deep_find_req_id(data)
        if deep:
            return deep

        outer_type = str(data.get("type", "")).lower()
        inner_type = str(nested_dict.get("type", "")).lower() if nested_dict else ""

        msg = None
        if nested_dict is not None:
            msg = nested_dict.get("message")
        if msg is None:
            msg = data.get("message")
        if msg is None or not str(msg).strip():
            return None
        msg_s = str(msg).strip()
        if outer_type == "success" or inner_type == "success":
            return msg_s
        if PhoneAuthService._looks_like_provider_req_token(msg_s):
            return msg_s
        return None

    @staticmethod
    def _deep_find_req_id(obj: Any, depth: int = 0) -> Optional[str]:
        if depth > 6 or not isinstance(obj, dict):
            return None
        for key in ("reqId", "request_id", "req_id", "requestId"):
            val = obj.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        for v in obj.values():
            if isinstance(v, dict):
                hit = PhoneAuthService._deep_find_req_id(v, depth + 1)
                if hit:
                    return hit
            if isinstance(v, list):
                for el in v:
                    if isinstance(el, dict):
                        hit = PhoneAuthService._deep_find_req_id(el, depth + 1)
                        if hit:
                            return hit
        return None

    @staticmethod
    def _looks_like_provider_req_token(value: str) -> bool:
        if len(value) < 8 or " " in value:
            return False
        if all(c in "0123456789abcdefABCDEF" for c in value):
            return len(value) >= 12
        return value.replace("-", "").replace("_", "").isalnum()

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
