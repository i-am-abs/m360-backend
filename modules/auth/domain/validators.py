from http import HTTPStatus

from exceptions.api_exception import ApiException


class IndiaPhoneNumberValidator:
    def __init__(self, country_code: str) -> None:
        self._country_code = (country_code or "").strip()

    def _require_country_code(self) -> str:
        if not self._country_code:
            raise ApiException(
                "MSG91_COUNTRY_CODE is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return self._country_code

    def validate_and_format(self, phone_number: str) -> str:
        raw = (phone_number or "").strip()
        if not raw.isdigit():
            raise ApiException(
                "Phone number must contain numbers only",
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        if len(raw) != 10:
            raise ApiException(
                "Phone number must be exactly 10 digits",
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        return f"{self._require_country_code()}{raw}"
