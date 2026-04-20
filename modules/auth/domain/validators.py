import os
from http import HTTPStatus

from constants.env_keys import EnvKeys
from exceptions.api_exception import ApiException
from services.google_places.support.env import load_project_dotenv


class IndiaPhoneNumberValidator:
    @staticmethod
    def _country_code() -> str:
        load_project_dotenv()
        code = os.getenv(EnvKeys.MSG91_COUNTRY_CODE.value, "").strip()
        if not code:
            raise ApiException(
                "MSG91_COUNTRY_CODE is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        return code

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
        return f"{self._country_code()}{raw}"
