from __future__ import annotations

from http import HTTPStatus

from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.phone_validator import PhoneValidator


class IndiaPhoneValidator(PhoneValidator):
    def __init__(self, country_code: str = "91") -> None:
        self._country_code = country_code

    def validate_and_format(self, phone_number: str) -> str:
        raw = (phone_number or "").strip()
        if not raw.isdigit():
            raise ApiException(
                "Phone number must contain numbers only",
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.INVALID_PHONE,
            )
        if len(raw) != 10:
            raise ApiException(
                "Phone number must be exactly 10 digits",
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.INVALID_PHONE,
            )
        return f"{self._country_code}{raw}"
