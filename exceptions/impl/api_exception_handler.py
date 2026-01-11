from fastapi import Request
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from exceptions.api_exception import ApiException


async def api_exception_handler(request: Request, exc: ApiException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "UPSTREAM_ERROR",
            "message": str(exc),
            "status_code": exc.status_code,
            "error": exc.__class__.__name__,
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "ERROR",
            "message": str(exc),
            "status_code": 500,
            "error": exc.__class__.__name__,
            "path": request.url.path,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    # Standardize FastAPI HTTPException payloads
    status_code = exc.status_code if hasattr(exc, "status_code") else 500
    # detail can be str or dict; normalize to str
    detail = exc.detail if hasattr(exc, "detail") else None
    message = detail if isinstance(detail, str) else (
        detail.get("message") if isinstance(detail, dict) and "message" in detail else str(detail)
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ERROR",
            "message": message or "HTTP error",
            "status_code": status_code,
            "error": exc.__class__.__name__,
            "path": request.url.path,
        },
    )
