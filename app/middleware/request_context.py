from __future__ import annotations

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, set_request_id

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
            self,
            request: Request,
            call_next: Callable[[Request], Response],
    ) -> Response:
        requestId = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(requestId)
        requestStartTime = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed method=%s path=%s",
                request.method,
                request.url.path,
            )
            raise

        requestDurationMilliseconds = (time.perf_counter() - requestStartTime) * 1000
        if response.status_code >= 500:
            logger.warning(
                "request_error method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                requestDurationMilliseconds,
            )

        response.headers["X-Request-ID"] = requestId
        set_request_id(None)
        return response
