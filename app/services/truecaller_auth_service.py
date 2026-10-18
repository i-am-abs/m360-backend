from __future__ import annotations

import re
import uuid
from typing import Any, Dict, Optional

from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.integrations.truecaller_state_store import TruecallerStateStore
from app.interfaces.phone_validator import PhoneValidator
from app.interfaces.truecaller_gateway import (
    TruecallerFailure,
    TruecallerGateway,
    TruecallerGatewayError,
)
from app.interfaces.truecaller_identity_repository import (
    TruecallerIdentityConflict,
    TruecallerIdentityRepository,
)
from app.services.phone_auth_service import PhoneAuthService

log = get_logger(__name__)

_MAX_CODE_LENGTH = 2048
_MAX_SUB_LENGTH = 256
_PKCE_VERIFIER = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")
_RESTRICTED_STATUSES = frozenset({"blocked", "suspended", "deleted", "disabled"})

ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Invalid request. Please try again.",
    ErrorCode.TRUECALLER_NOT_CONFIGURED: "Truecaller login is currently unavailable. Please use OTP.",
    ErrorCode.TRUECALLER_STATE_MISMATCH: "This login attempt is no longer valid. Please try again.",
    ErrorCode.TRUECALLER_EXCHANGE_FAILED: "Could not verify your Truecaller account. Please use OTP.",
    ErrorCode.TRUECALLER_PROFILE_FAILED: "Could not read your Truecaller profile. Please use OTP.",
    ErrorCode.TRUECALLER_UNAVAILABLE: "Truecaller is not responding right now. Please try again or use OTP.",
    ErrorCode.TRUECALLER_ACCOUNT_CONFLICT: (
        "This Truecaller account is linked to a different phone number. Please use OTP."
    ),
    ErrorCode.INVALID_PHONE: "This phone number is not supported. Please use OTP.",
    ErrorCode.USER_CREATION_FAILED: "We couldn't set up your account right now. Please try again.",
    ErrorCode.USER_NOT_ALLOWED: "Your account is not allowed to sign in. Please contact support.",
    ErrorCode.TOKEN_GENERATION_FAILED: "We couldn't sign you in right now. Please try again.",
    ErrorCode.INTERNAL_ERROR: "Something went wrong. Please try again.",
}

_GATEWAY_ERRORS: Dict[TruecallerFailure, ErrorCode] = {
    TruecallerFailure.EXCHANGE: ErrorCode.TRUECALLER_EXCHANGE_FAILED,
    TruecallerFailure.PROFILE: ErrorCode.TRUECALLER_PROFILE_FAILED,
    TruecallerFailure.UNAVAILABLE: ErrorCode.TRUECALLER_UNAVAILABLE,
}


class TruecallerLoginError(Exception):
    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code
        self.message = ERROR_MESSAGES[code]


class TruecallerAuthService:
    def __init__(
            self,
            gateway: TruecallerGateway,
            identities: TruecallerIdentityRepository,
            state_store: TruecallerStateStore,
            phone_validator: PhoneValidator,
            phone_auth: PhoneAuthService,
    ) -> None:
        self._gateway = gateway
        self._identities = identities
        self._state_store = state_store
        self._phone_validator = phone_validator
        self._phone_auth = phone_auth

    def login(self, authorization_code: str, code_verifier: str, oauth_state: str) -> Dict[str, Any]:
        authorization_code = (authorization_code or "").strip()
        code_verifier = (code_verifier or "").strip()
        if not authorization_code or len(authorization_code) > _MAX_CODE_LENGTH:
            raise TruecallerLoginError(ErrorCode.VALIDATION_ERROR)
        if not _PKCE_VERIFIER.match(code_verifier):
            raise TruecallerLoginError(ErrorCode.TRUECALLER_EXCHANGE_FAILED)
        state = self._normalize_state(oauth_state)
        if state is None or not self._state_store.claim(state):
            raise TruecallerLoginError(ErrorCode.TRUECALLER_STATE_MISMATCH)

        try:
            tc_access_token = self._gateway.exchange_code(authorization_code, code_verifier)
            profile = self._gateway.fetch_profile(tc_access_token)
        except TruecallerGatewayError as exc:
            raise TruecallerLoginError(_GATEWAY_ERRORS[exc.failure]) from None

        sub, phone = self._verified_identity(profile)

        try:
            identity = self._identities.find_by_sub(sub)
        except Exception as exc:
            log.error("Truecaller identity lookup failed: %s", type(exc).__name__)
            raise TruecallerLoginError(ErrorCode.USER_CREATION_FAILED) from None
        if identity is not None and identity.get("phone_number") != phone:
            log.warning("Truecaller identity bound to another phone | phone=%s", phone)
            raise TruecallerLoginError(ErrorCode.TRUECALLER_ACCOUNT_CONFLICT)

        try:
            user = self._phone_auth.provision_user(phone)
        except Exception as exc:
            log.error("Truecaller user provisioning failed | phone=%s: %s", phone, type(exc).__name__)
            raise TruecallerLoginError(ErrorCode.USER_CREATION_FAILED) from None
        user_id = str(user.get("user_id") or "")
        if not user_id:
            raise TruecallerLoginError(ErrorCode.USER_CREATION_FAILED)
        if self._is_restricted(user):
            log.warning("Truecaller login refused for restricted userId=%s", user_id)
            raise TruecallerLoginError(ErrorCode.USER_NOT_ALLOWED)

        try:
            self._identities.link(sub, user_id, phone)
        except TruecallerIdentityConflict:
            log.warning("Truecaller identity bound to another phone | userId=%s", user_id)
            raise TruecallerLoginError(ErrorCode.TRUECALLER_ACCOUNT_CONFLICT) from None
        except Exception as exc:
            log.error("Truecaller identity link failed | userId=%s: %s", user_id, type(exc).__name__)
            raise TruecallerLoginError(ErrorCode.USER_CREATION_FAILED) from None

        try:
            auth = self._phone_auth.issue_session(user_id, phone)
            access_token = str(auth["access_token"])
        except Exception as exc:
            log.error("Truecaller session issue failed | userId=%s: %s", user_id, type(exc).__name__)
            raise TruecallerLoginError(ErrorCode.TOKEN_GENERATION_FAILED) from None

        log.info("Truecaller login ok | phone=%s | userId=%s", phone, user_id)
        return {
            "user": {"user_id": user_id, "phone_number": f"+{phone}"},
            "auth": {"access_token": access_token},
        }

    def _verified_identity(self, profile: Dict[str, Any]) -> tuple[str, str]:
        sub = profile.get("sub")
        raw_phone = profile.get("phone_number")
        if (
                not isinstance(sub, str)
                or not sub.strip()
                or len(sub) > _MAX_SUB_LENGTH
                or not isinstance(raw_phone, (str, int))
                or not str(raw_phone).strip()
                or profile.get("phone_number_verified") is False
        ):
            log.warning("Truecaller profile missing verified identity")
            raise TruecallerLoginError(ErrorCode.TRUECALLER_PROFILE_FAILED)
        try:
            phone = self._phone_validator.validate_and_format(str(raw_phone).strip())
        except ApiException:
            raise TruecallerLoginError(ErrorCode.INVALID_PHONE) from None
        return sub.strip(), phone

    @staticmethod
    def _normalize_state(oauth_state: Optional[str]) -> Optional[str]:
        try:
            return str(uuid.UUID(str(oauth_state or "").strip()))
        except ValueError:
            return None

    @staticmethod
    def _is_restricted(user: Dict[str, Any]) -> bool:
        if user.get("blocked_at") or user.get("suspended_at") or user.get("deleted_at"):
            return True
        return str(user.get("status") or "").lower() in _RESTRICTED_STATUSES
