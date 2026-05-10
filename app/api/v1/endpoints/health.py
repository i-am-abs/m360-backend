from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.enums.api_endpoints import ApiEndpoint
from app.utils.response import success_response

router = APIRouter(tags=["health"])


def persistence_label(request: Request, settings) -> str:
    backend = getattr(request.app.state, "user_store_backend", None)
    if backend:
        return backend
    if settings.mongodb_configured:
        return "mongodb"
    if settings.redis_configured:
        return "redis"
    return "local_cache"


@router.get(ApiEndpoint.HEALTH_LIVE.value, summary="Liveness (no dependencies)")
def health_live():
    return JSONResponse(
        status_code=HTTPStatus.OK.value,
        content={"status": "up", "check": "live"},
    )


@router.get(ApiEndpoint.HEALTH_READY.value, summary="Readiness (Redis / MongoDB)")
def health_ready(request: Request):
    s = request.app.state.settings
    data: dict = {
        "status": "UP",
        "check": "ready",
        "persistence": persistence_label(request, s),
        "api_response_cache": getattr(request.app.state, "api_response_cache", False),
    }
    redis_client = getattr(request.app.state, "redis", None)
    if s.redis_configured:
        if redis_client is None:
            data["redis"] = "not_initialized"
            return success_response(data, message="Service unavailable", status_code=503)
        try:
            redis_client.ping()
            data["redis"] = "connected"
        except Exception:
            data["redis"] = "unreachable"
            return success_response(data, message="Service unavailable", status_code=503)

    if s.mongodb_configured:
        client = getattr(request.app.state, "mongo_client", None)
        if client is None:
            data["mongodb"] = "not_initialized"
            return success_response(data, message="Service unavailable", status_code=503)
        try:
            client.admin.command("ping")
            data["mongodb"] = "connected"
        except Exception:
            data["mongodb"] = "unreachable"
            return success_response(data, message="Service unavailable", status_code=503)

    return success_response(data)


@router.get(ApiEndpoint.HEALTH.value, summary="Health check (full)")
def health(request: Request):
    s = request.app.state.settings
    data = {
        "status": "UP",
        "persistence": persistence_label(request, s),
        "api_response_cache": getattr(request.app.state, "api_response_cache", False),
    }
    redis_client = getattr(request.app.state, "redis", None)
    if s.redis_configured:
        if redis_client is None:
            return success_response(
                {**data, "redis": "not_initialized"},
                message="Service unavailable",
                status_code=503,
            )
        try:
            redis_client.ping()
            data["redis"] = "connected"
        except Exception:
            return success_response(
                {**data, "redis": "unreachable"},
                message="Service unavailable",
                status_code=503,
            )

    if s.mongodb_configured:
        client = getattr(request.app.state, "mongo_client", None)
        if client is None:
            return success_response(
                {**data, "mongodb": "not_initialized"},
                message="Service unavailable",
                status_code=503,
            )
        try:
            client.admin.command("ping")
            data["mongodb"] = "connected"
        except Exception:
            return success_response(
                {**data, "mongodb": "unreachable"},
                message="Service unavailable",
                status_code=503,
            )
    return success_response(data)
