from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.module_registry import resolveModuleActivationState
from app.utils.response import success_response

router = APIRouter(tags=["health"])


def buildHealthPayload(request: Request) -> dict:
    settings = request.app.state.settings
    moduleActivationState = resolveModuleActivationState(settings)
    return {
        "status": "UP",
        "persistence": getattr(request.app.state, "user_store_backend", "disabled"),
        "api_response_cache": getattr(request.app.state, "api_response_cache", False),
        "active_modules": moduleActivationState.activeModuleNames(),
        "modules": {
            "quran": moduleActivationState.quranModuleActive,
            "masjid": moduleActivationState.masjidModuleActive,
            "auth": moduleActivationState.authModuleActive,
            "msg91_webhook": moduleActivationState.msg91WebhookModuleActive,
            "feature_flags": moduleActivationState.featureFlagModuleActive,
            "redis_cache": moduleActivationState.redisCacheModuleActive,
            "mongodb": moduleActivationState.mongodbModuleActive,
        },
    }


@router.get("/health/live", summary="Liveness")
def health_live():
    return JSONResponse(
        status_code=HTTPStatus.OK.value,
        content={"status": "up", "check": "live"},
    )


@router.get("/health/ready", summary="Readiness")
def health_ready(request: Request):
    settings = request.app.state.settings
    data = {
        **buildHealthPayload(request),
        "check": "ready",
    }
    if settings.redis_configured:
        redisClient = getattr(request.app.state, "redis", None)
        if redisClient is None:
            data["redis"] = "not_initialized"
            return success_response(data, message="Service unavailable", status_code=503)
        try:
            redisClient.ping()
            data["redis"] = "connected"
        except Exception:
            data["redis"] = "unreachable"
            return success_response(data, message="Service unavailable", status_code=503)

    if settings.mongodb_configured:
        mongoClient = getattr(request.app.state, "mongo_client", None)
        if mongoClient is None:
            data["mongodb"] = "not_initialized"
            return success_response(data, message="Service unavailable", status_code=503)
        try:
            mongoClient.admin.command("ping")
            data["mongodb"] = "connected"
        except Exception:
            data["mongodb"] = "unreachable"
            return success_response(data, message="Service unavailable", status_code=503)

    return success_response(data)


@router.get("/health", summary="Health check")
def health(request: Request):
    settings = request.app.state.settings
    data = buildHealthPayload(request)
    if settings.redis_configured:
        redisClient = getattr(request.app.state, "redis", None)
        if redisClient is None:
            return success_response(
                {**data, "redis": "not_initialized"},
                message="Service unavailable",
                status_code=503,
            )
        try:
            redisClient.ping()
            data["redis"] = "connected"
        except Exception:
            return success_response(
                {**data, "redis": "unreachable"},
                message="Service unavailable",
                status_code=503,
            )

    if settings.mongodb_configured:
        mongoClient = getattr(request.app.state, "mongo_client", None)
        if mongoClient is None:
            return success_response(
                {**data, "mongodb": "not_initialized"},
                message="Service unavailable",
                status_code=503,
            )
        try:
            mongoClient.admin.command("ping")
            data["mongodb"] = "connected"
        except Exception:
            return success_response(
                {**data, "mongodb": "unreachable"},
                message="Service unavailable",
                status_code=503,
            )
    return success_response(data)
