from __future__ import annotations

from http import HTTPStatus
from typing import Optional, Union

from app.core.enums.error_code import ErrorCode, STATUS_TO_ERROR_CODE


class ApiException(RuntimeError):
    def __init__(
            self,
            message: str,
            status_code: int = HTTPStatus.BAD_GATEWAY.value,
            *,
            code: Optional[Union[ErrorCode, str]] = None,
            provider_message: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code: str = self._resolve_code(code, status_code)
        self.provider_message = provider_message

    @staticmethod
    def _resolve_code(
            code: Optional[Union[ErrorCode, str]],
            status_code: int,
    ) -> str:
        if code is not None:
            return code.value if isinstance(code, ErrorCode) else code
        default = STATUS_TO_ERROR_CODE.get(status_code, ErrorCode.UPSTREAM_ERROR)
        return default.value
