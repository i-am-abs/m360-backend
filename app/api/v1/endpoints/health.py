from fastapi import APIRouter, Request

from app.core.enums.api_endpoints import ApiEndpoint
from app.utils.response import success_response

router = APIRouter(tags=["health"])


@router.get(ApiEndpoint.HEALTH.value, summary="Health check")
def health(request: Request):
    s = request.app.state.settings
    data = {
        "status": "UP",
        "persistence": "mongodb" if s.mongodb_enabled else "local_cache",
    }
    if s.mongodb_enabled:
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
