from __future__ import annotations

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, set_request_id

_log = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
            self,
            request: Request,
            call_next: Callable[[Request], Response],
    ) -> Response:
        header_rid = request.headers.get("X-Request-ID")
        req_id = header_rid or str(uuid.uuid4())
        set_request_id(req_id)
        t0 = time.perf_counter()

        _log.info(
            "request_started method=%s path=%s",
            request.method,
            request.url.path,
        )
        try:
            response = await call_next(request)
        except Exception:
            _log.exception(
                "request_failed method=%s path=%s",
                request.method,
                request.url.path,
            )
            raise

        elapsed_ms = (time.perf_counter() - t0) * 1000
        _log.info(
            "request_finished method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = req_id
        set_request_id(None)
        return response
