from __future__ import annotations

from http import HTTPStatus
from typing import Optional

STATUS_TO_ERROR_CODE: dict[int, str] = {
    HTTPStatus.BAD_REQUEST.value: "BAD_REQUEST",
    HTTPStatus.UNAUTHORIZED.value: "UNAUTHORIZED",
    HTTPStatus.FORBIDDEN.value: "FORBIDDEN",
    HTTPStatus.NOT_FOUND.value: "NOT_FOUND",
    HTTPStatus.UNPROCESSABLE_ENTITY.value: "VALIDATION_ERROR",
    HTTPStatus.INTERNAL_SERVER_ERROR.value: "INTERNAL_ERROR",
    HTTPStatus.BAD_GATEWAY.value: "BAD_GATEWAY",
    HTTPStatus.SERVICE_UNAVAILABLE.value: "SERVICE_UNAVAILABLE",
    HTTPStatus.GATEWAY_TIMEOUT.value: "GATEWAY_TIMEOUT",
}


class ApiException(RuntimeError):
    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_GATEWAY.value, *, code: Optional[str] = None, provider_message: Optional[str] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code: str = self.resolve_code(code, status_code)
        self.provider_message = provider_message

    @staticmethod
    def resolve_code(code: Optional[str], status_code: int) -> str:
        if code is not None:
            return code
        return STATUS_TO_ERROR_CODE.get(status_code, "UPSTREAM_ERROR")
