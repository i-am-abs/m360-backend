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
from app.utils.session_ttl import session_never_expires

log = get_logger(__name__)


class PhoneAuthService:
    def __init__(
            self,
            userRepository: UserRepository,
            otpGateway: OtpGateway,
            phoneValidator: PhoneValidator,
            sessionTtlSeconds: int,
            msg91PendingReqIdStore: Optional[Msg91PendingReqIdStore] = None,
            msg91AsyncReqIdWaitSeconds: float = 0.0,
    ) -> None:
        self.userRepository = userRepository
        self.otpGateway = otpGateway
        self.phoneValidator = phoneValidator
        self.sessionTtlSeconds = sessionTtlSeconds
        self.msg91PendingReqIdStore = msg91PendingReqIdStore
        self.msg91AsyncReqIdWaitSeconds = msg91AsyncReqIdWaitSeconds

    def requestOtp(self, phoneNumber: str) -> Dict[str, Any]:
        formatted = self.phoneValidator.validate_and_format(phoneNumber)
        if self.msg91PendingReqIdStore is not None:
            self.msg91PendingReqIdStore.discard_identifier(formatted)
        data = self.otpGateway.send_otp(formatted)
        reqId = self.extractRequestId(data)
        if (
                not reqId
                and self.msg91PendingReqIdStore is not None
                and self.msg91AsyncReqIdWaitSeconds > 0
        ):
            reqId = self.msg91PendingReqIdStore.wait_for(
                formatted,
                total_seconds=self.msg91AsyncReqIdWaitSeconds,
                interval=0.2,
            )
        if not reqId:
            raise ApiException(
                "OTP provider did not return request ID",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                code=ErrorCode.MSG91_ERROR,
                provider_message=str(data.get("errors") or data.get("message") or data),
            )
        log.info("OTP sent for %s | reqId=%s", phoneNumber, reqId)
        return {"phone_number": phoneNumber, "req_id": reqId, "provider_response": data}

    def retryOtp(
            self,
            phoneNumber: str,
            reqId: str,
            retryChannel: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self.otpGateway.retry_otp(reqId, retryChannel)
        log.info("OTP retry for %s | reqId=%s | channel=%s", phoneNumber, reqId, retryChannel)
        return {"phone_number": phoneNumber, "req_id": reqId, "provider_response": data}

    def verifyOtp(self, phoneNumber: str, reqId: str, otp: str) -> Dict[str, Any]:
        self.phoneValidator.validate_and_format(phoneNumber)
        data = self.otpGateway.verify_otp(reqId, otp)
        self.assertVerificationSuccess(data)
        user = self.userRepository.ensureUser(phoneNumber)
        session = self.userRepository.createSession(user["user_id"], self.sessionTtlSeconds)
        log.info("OTP verified for %s | userId=%s", phoneNumber, user["user_id"])
        return {
            "user": user,
            "auth": self.getAuthPayload(session),
        }

    def refreshAccessToken(self, accessToken: str) -> Dict[str, Any]:
        session = self.userRepository.refreshSession(accessToken, self.sessionTtlSeconds)
        if not session:
            raise ApiException(
                "Invalid or expired access token",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )
        user = self.userRepository.getUserBySession(session["access_token"])
        if not user:
            raise ApiException(
                "Invalid or expired access token",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )
        log.info(
            "Access token refreshed for userId=%s (never_expires=%s)",
            user["user_id"],
            session_never_expires(self.sessionTtlSeconds),
        )
        return {"user": user, "auth": self.getAuthPayload(session)}

    def getAuthPayload(self, session: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "access_token": session["access_token"],
            "token_type": "bearer",
            "expires_in": session.get("expires_in"),
        }

    def extractRequestId(self, data: Dict[str, Any]) -> Optional[str]:
        if data is None or not isinstance(data, dict):
            return None
        nestedRaw = data.get("data")
        nestedDict = nestedRaw if isinstance(nestedRaw, dict) else None

        layers: list[Dict[str, Any]] = [data]
        if nestedDict is not None:
            layers.append(nestedDict)
        for extraKey in ("response", "result"):
            block = data.get(extraKey)
            if isinstance(block, dict):
                layers.append(block)

        for layer in layers:
            for key in ("reqId", "request_id", "req_id", "requestId"):
                val = layer.get(key)
                if val is not None and str(val).strip():
                    return str(val).strip()

        deep = self.deepFindRequestId(data)
        if deep:
            return deep

        outerType = str(data.get("type", "")).lower()
        innerType = str(nestedDict.get("type", "")).lower() if nestedDict else ""

        msg = None
        if nestedDict is not None:
            msg = nestedDict.get("message")
        if msg is None:
            msg = data.get("message")
        if msg is None or not str(msg).strip():
            return None
        msgS = str(msg).strip()
        if outerType == "success" or innerType == "success":
            return msgS
        if self.looksLikeProviderRequestToken(msgS):
            return msgS
        return None

    def deepFindRequestId(self, obj: Any, depth: int = 0) -> Optional[str]:
        if depth > 6 or not isinstance(obj, dict):
            return None
        for key in ("reqId", "request_id", "req_id", "requestId"):
            val = obj.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        for v in obj.values():
            if isinstance(v, dict):
                hit = self.deepFindRequestId(v, depth + 1)
                if hit:
                    return hit
            if isinstance(v, list):
                for el in v:
                    if isinstance(el, dict):
                        hit = self.deepFindRequestId(el, depth + 1)
                        if hit:
                            return hit
        return None

    def looksLikeProviderRequestToken(self, value: str) -> bool:
        if len(value) < 8 or " " in value:
            return False
        if all(c in "0123456789abcdefABCDEF" for c in value):
            return len(value) >= 12
        return value.replace("-", "").replace("_", "").isalnum()

    def assertVerificationSuccess(self, data: Dict[str, Any]) -> None:
        msg = str((data or {}).get("message", "")).lower()
        otpType = str((data or {}).get("type", "")).lower()
        if "success" not in msg and otpType != "success":
            raise ApiException(
                "OTP verification failed",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.OTP_INVALID,
                provider_message=(data or {}).get("message"),
            )
