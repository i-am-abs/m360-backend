from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse


def success_response(
        data: Any,
        message: str = "OK",
        status_code: int = HTTPStatus.OK.value,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success",
            "message": message,
            "data": data,
        },
    )


def error_envelope(
        code: str,
        message: str,
        status_code: int = HTTPStatus.OK.value,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


def no_store(response: JSONResponse) -> JSONResponse:
    """Mark a response as uncacheable by clients and intermediary proxies."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
