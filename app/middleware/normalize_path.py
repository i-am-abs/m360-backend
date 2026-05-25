from __future__ import annotations

import re
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_MULTI_SLASH = re.compile(r"/{2,}")


class NormalizePathMiddleware(BaseHTTPMiddleware):
    async def dispatch(
            self,
            request: Request,
            call_next: Callable[[Request], Response],
    ) -> Response:
        path = request.scope.get("path") or ""
        normalized = _MULTI_SLASH.sub("/", path)
        if normalized != path:
            request.scope["path"] = normalized
        return await call_next(request)
