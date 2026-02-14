from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth_routes import get_current_user
from core.di.container import get_masjid_service
from utils.http_response import success_response

masjid_router = APIRouter(prefix="/masjid", tags=["masjid"])


@masjid_router.get("/nearby")
def get_nearby_masjids(
    latitude: float = Query(..., description="User latitude"),
    longitude: float = Query(..., description="User longitude"),
    radius_km: float | None = Query(None, description="Override radius (km) - uses env default if not provided"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    _: dict = Depends(get_current_user),
):
    service = get_masjid_service()
    result = service.find_nearby(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
    )
    return success_response(result)
