from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.exceptions.base import ApiException

_log = get_logger("errors")


def _error_body(
        code: str,
        message: str,
        provider_message: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }


_HTTP_STATUS_ERROR_MAP: Dict[int, ErrorCode] = {
    HTTPStatus.FORBIDDEN.value: ErrorCode.FORBIDDEN,
    HTTPStatus.NOT_FOUND.value: ErrorCode.NOT_FOUND,
    HTTPStatus.UNPROCESSABLE_ENTITY.value: ErrorCode.VALIDATION_ERROR,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api_exception(_req: Any, exc: ApiException) -> JSONResponse:
        _log.warning(
            "api_exception code=%s status=%s msg=%s",
            exc.code, exc.status_code, str(exc),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, str(exc), exc.provider_message),
        )

    @app.exception_handler(HTTPException)
    async def _http_exception(request: Any, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        message = (
            str(detail.get("message") or detail.get("detail") or detail)
            if isinstance(detail, dict)
            else (str(detail) if detail else "Request error")
        )
        code = _HTTP_STATUS_ERROR_MAP.get(
            exc.status_code, ErrorCode.HTTP_ERROR,
        )
        _log.info(
            "http_exception path=%s status=%s code=%s",
            request.url.path, exc.status_code, code.value,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code.value, message),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_req: Any, exc: RequestValidationError) -> JSONResponse:
        fields = jsonable_encoder(exc.errors())
        _log.info("validation_error errors=%s", fields)
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            content={
                "status": "error",
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Invalid request payload",
                    # "exact_message_from_service_provider": None,
                    "fields": fields,
                },
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Any, exc: Exception) -> JSONResponse:
        _log.exception("unhandled_exception path=%s", request.url.path)
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            content=_error_body(
                ErrorCode.INTERNAL_ERROR.value,
                "An unexpected error occurred. Try again later.",
            ),
        )
