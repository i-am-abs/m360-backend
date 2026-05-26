from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.exceptions.base import ApiException

logger = get_logger("errors")


def buildErrorResponseBody(errorCode: str, message: str, providerMessage: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "code": errorCode,
            "message": message,
            "exact_message_from_service_provider": providerMessage,
        },
    }


HTTP_STATUS_TO_ERROR_CODE: Dict[int, str] = {
    HTTPStatus.FORBIDDEN.value: "FORBIDDEN",
    HTTPStatus.NOT_FOUND.value: "NOT_FOUND",
    HTTPStatus.UNPROCESSABLE_ENTITY.value: "VALIDATION_ERROR",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def handleApiException(_request: Any, exception: ApiException) -> JSONResponse:
        if exception.status_code >= 500:
            logger.error(
                "api_exception code=%s status=%s message=%s",
                exception.code,
                exception.status_code,
                str(exception),
            )
        return JSONResponse(
            status_code=exception.status_code,
            content=buildErrorResponseBody(
                exception.code,
                str(exception),
                exception.provider_message,
            ),
        )

    @app.exception_handler(HTTPException)
    async def handleHttpException(_request: Any, exception: HTTPException) -> JSONResponse:
        detail = exception.detail
        message = (
            str(detail.get("message") or detail.get("detail") or detail)
            if isinstance(detail, dict)
            else (str(detail) if detail else "Request error")
        )
        errorCode = HTTP_STATUS_TO_ERROR_CODE.get(exception.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exception.status_code,
            content=buildErrorResponseBody(errorCode, message),
        )

    @app.exception_handler(RequestValidationError)
    async def handleValidationError(_request: Any, exception: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            content={
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request payload",
                    "exact_message_from_service_provider": None,
                    "fields": jsonable_encoder(exception.errors()),
                },
            },
        )

    @app.exception_handler(Exception)
    async def handleUnhandledException(request: Any, _exception: Exception) -> JSONResponse:
        logger.exception("unhandled_exception path=%s", request.url.path)
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            content=buildErrorResponseBody(
                "INTERNAL_ERROR",
                "An unexpected error occurred. Try again later.",
            ),
        )
