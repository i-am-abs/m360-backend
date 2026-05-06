from fastapi import APIRouter

from app.core.enums.api_endpoints import ApiEndpoint
from app.utils.response import success_response

router = APIRouter(tags=["health"])


@router.get(ApiEndpoint.HEALTH.value, summary="Health check")
def health():
    return success_response({"status": "UP"})
