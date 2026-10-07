from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict

from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.phone_validator import PhoneValidator
from app.interfaces.truecaller_gateway import TruecallerGateway
from app.services.phone_auth_service import PhoneAuthService

log = get_logger(__name__)


class TruecallerAuthService:
    def __init__(
            self,
            gateway: TruecallerGateway,
            phone_validator: PhoneValidator,
            phone_auth: PhoneAuthService,
    ) -> None:
        self._gateway = gateway
        self._phone_validator = phone_validator
        self._phone_auth = phone_auth

    def login(self, authorization_code: str, code_verifier: str) -> Dict[str, Any]:
        tc_access_token = self._gateway.exchange_code(
            authorization_code.strip(), code_verifier.strip(),
        )
        profile = self._gateway.fetch_profile(tc_access_token)

        raw_phone = str(profile.get("phone_number") or "").strip()
        if not raw_phone or profile.get("phone_number_verified") is False:
            raise ApiException(
                "Truecaller profile has no verified phone number",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code=ErrorCode.TRUECALLER_AUTH_FAILED,
            )
        formatted_phone = self._phone_validator.validate_and_format(raw_phone)

        result = self._phone_auth.login_verified_phone(formatted_phone)
        result["profile"] = self._profile_payload(profile)
        log.info(
            "Truecaller login for %s | userId=%s | tcSub=%s",
            formatted_phone,
            result["user"]["user_id"],
            profile.get("sub"),
        )
        return result

    @staticmethod
    def _profile_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
        name = " ".join(
            part.strip()
            for part in (profile.get("given_name"), profile.get("family_name"))
            if isinstance(part, str) and part.strip()
        )
        return {
            "name": name or None,
            "email": profile.get("email"),
            "picture": profile.get("picture"),
        }
