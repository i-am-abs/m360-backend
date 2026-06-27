from __future__ import annotations

import hashlib
from http import HTTPStatus
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.enums.error_code import ErrorCode
from app.services.rate_limiter import RateLimiter
from app.utils.structured_log import log_event

_HEALTH_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/api/v1/health",
    "/api/v1/health/live",
    "/api/v1/health/ready",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter

    async def dispatch(
            self,
            request: Request,
            call_next: Callable[[Request], Response],
    ) -> Response:
        if self._rate_limiter is None:
            return await call_next(request)

        path = request.url.path
        if self._should_skip(path):
            return await call_next(request)

        client_key = self._client_key(request)
        allowed, retry_after = self._rate_limiter.check(client_key, path)
        if allowed:
            return await call_next(request)

        log_event(
            "rate_limit",
            "request_blocked",
            resource_id=client_key,
            path=path,
            method=request.method,
            retry_after_seconds=retry_after,
        )
        return JSONResponse(
            status_code=HTTPStatus.TOO_MANY_REQUESTS.value,
            content={
                "status": "error",
                "error": {
                    "code": ErrorCode.RATE_LIMIT_EXCEEDED.value,
                    "message": "Too many requests. Please try again later.",
                },
            },
            headers={"Retry-After": str(retry_after)},
        )

    @staticmethod
    def _should_skip(path: str) -> bool:
        normalized = path.rstrip("/") or "/"
        return normalized in _HEALTH_PATHS

    @staticmethod
    def _client_key(request: Request) -> str:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if token:
                digest = hashlib.sha256(token.encode()).hexdigest()[:24]
                return f"token:{digest}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            if ip:
                return f"ip:{ip}"

        if request.client and request.client.host:
            return f"ip:{request.client.host}"
        return "ip:unknown"
