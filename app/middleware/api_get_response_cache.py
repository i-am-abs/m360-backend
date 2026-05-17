from __future__ import annotations

import json
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.interfaces.cache_store import CacheStore
from app.utils.cache_keys import create_request_get_cache_key


class ApiGetResponseCacheMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            cache_store: CacheStore,
            ttl_seconds: int,
            key_prefix: str,
            excluded_paths: Iterable[str],
    ) -> None:
        super().__init__(app)
        self.cache_store = cache_store
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.key_prefix = (key_prefix or "m360").strip() or "m360"
        self.excluded_paths = tuple(excluded_paths)

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() != "GET" or self.should_skip_path(request.url.path):
            return await call_next(request)

        cache_key = create_request_get_cache_key(
            self.key_prefix,
            request.url.path,
            request.query_params.multi_items(),
            request.headers.get("authorization", ""),
        )
        cached_payload = self.cache_store.get_json(cache_key)
        if cached_payload is not None:
            return JSONResponse(
                status_code=int(cached_payload["status_code"]),
                content=cached_payload["content"],
            )

        response = await call_next(request)
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        replay_response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        if self.is_cacheable_response(response, response_body):
            self.cache_store.set_json(
                cache_key,
                {
                    "status_code": response.status_code,
                    "content": json.loads(response_body.decode("utf-8")),
                },
                self.ttl_seconds,
            )
        return replay_response

    def should_skip_path(self, path: str) -> bool:
        return any(
            path == excluded_path or path.startswith(f"{excluded_path}/")
            for excluded_path in self.excluded_paths
        )

    def is_cacheable_response(self, response: Response, response_body: bytes) -> bool:
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200 or "application/json" not in content_type.lower():
            return False
        try:
            json.loads(response_body.decode("utf-8"))
            return True
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False
