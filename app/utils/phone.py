from __future__ import annotations

from http import HTTPStatus
from typing import List, Set

from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.phone_validator import PhoneValidator


def canonicalize_india_phone(phone_number: str, country_code: str = "91") -> str:
    raw = (phone_number or "").strip().lstrip("+")
    cc = (country_code or "91").strip().lstrip("+")
    if not raw or not raw.isdigit():
        raise ValueError("Phone number must contain numbers only")
    if len(raw) == 10:
        return f"{cc}{raw}"
    if len(raw) == len(cc) + 10 and raw.startswith(cc):
        return raw
    raise ValueError("Phone number must be exactly 10 digits or include country code")


def phone_lookup_variants(phone_number: str, country_code: str = "91") -> List[str]:
    canonical = canonicalize_india_phone(phone_number, country_code)
    cc = country_code.strip().lstrip("+")
    variants: Set[str] = {canonical, (phone_number or "").strip()}
    if canonical.startswith(cc) and len(canonical) == len(cc) + 10:
        variants.add(canonical[len(cc):])
    return [variant for variant in variants if variant]


def phones_equivalent(left: str, right: str, country_code: str = "91") -> bool:
    try:
        return canonicalize_india_phone(left, country_code) == canonicalize_india_phone(
            right, country_code,
        )
    except ValueError:
        return (left or "").strip() == (right or "").strip()


class IndiaPhoneValidator(PhoneValidator):
    def __init__(self, country_code: str = "91") -> None:
        self._country_code = country_code

    def validate_and_format(self, phone_number: str) -> str:
        try:
            return canonicalize_india_phone(phone_number, self._country_code)
        except ValueError as exc:
            message = str(exc)
            raise ApiException(
                message,
                status_code=HTTPStatus.BAD_REQUEST.value,
                code=ErrorCode.INVALID_PHONE,
            ) from exc
