from __future__ import annotations

from http import HTTPStatus
from typing import Optional

from app.exceptions.base import ApiException


class FeatureFlagException(ApiException):
    def __init__(
            self,
            message: str,
            status_code: int = HTTPStatus.BAD_REQUEST.value,
            *,
            code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, code=code)
