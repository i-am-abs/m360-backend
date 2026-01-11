from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, message: str = "OK", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "SUCCESS",
            "message": message,
            "status_code": status_code,
            "data": data,
        },
    )
