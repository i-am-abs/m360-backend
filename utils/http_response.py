from typing import Any

from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK


def success_response(
        data: Any, message: str = "OK", status_code: int = HTTP_200_OK
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "SUCCESS",
            "message": message,
            "status_code": status_code,
            "data": data,
        },
    )
