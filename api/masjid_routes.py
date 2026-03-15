from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from constants.api_endpoints import ApiEndpoints
from db.repository.masjid_repository import MasjidRepository
from dto.masjid_models import (
    AMENITIES_MASTER,
    VALID_AMENITY_KEYS,
    AmenityToggleRequest,
    BulkAmenityRequest,
    MasjidCreateRequest,
)
from logger.Logger import Logger
from utils.http_response import success_response

logger = Logger.get_logger(__name__)
masjid_router = APIRouter(tags=["Masjid"])

_repo: Optional[MasjidRepository] = None


def get_masjid_repo() -> MasjidRepository:
    global _repo
    if _repo is None:
        _repo = MasjidRepository()
    return _repo


@masjid_router.get(
    ApiEndpoints.MASJID_AMENITIES_MASTER.value,
    summary="Master list of available amenities",
    description="Returns every amenity option the UI can render as checkboxes.",
)
def get_amenities_master():
    return success_response(AMENITIES_MASTER, message="Amenities master list")


@masjid_router.post(
    ApiEndpoints.MASJID_CREATE.value,
    summary="Create or update a masjid record",
    description="Creates a masjid document in MongoDB (upserts on masjid_id).",
)
def create_masjid(
    body: MasjidCreateRequest,
    repo: MasjidRepository = Depends(get_masjid_repo),
):
    try:
        data = {
            "name": body.name,
            "address": body.address,
            "latitude": body.latitude,
            "longitude": body.longitude,
            "amenities": [a.value for a in body.amenities],
        }
        repo.upsert_masjid(body.masjid_id, data)
        return success_response(
            {"masjid_id": body.masjid_id},
            message="Masjid saved",
            status_code=201,
        )
    except Exception as e:
        logger.error("Error creating masjid: %s", e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save masjid: {str(e)}",
        )


@masjid_router.get(
    ApiEndpoints.MASJID_AMENITIES.value,
    summary="Get amenities for a masjid",
    description="Returns the list of amenity keys enabled for a specific masjid.",
)
def get_masjid_amenities(
    masjid_id: str,
    repo: MasjidRepository = Depends(get_masjid_repo),
):
    try:
        doc = repo.find_by_masjid_id(masjid_id)
        if doc is None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Masjid '{masjid_id}' not found",
            )

        enabled_keys = doc.get("amenities", [])
        amenities_with_status = [
            {**a, "selected": a["key"] in enabled_keys} for a in AMENITIES_MASTER
        ]
        return success_response(amenities_with_status, message="Masjid amenities")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching amenities for %s: %s", masjid_id, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch amenities: {str(e)}",
        )


@masjid_router.put(
    ApiEndpoints.MASJID_AMENITIES.value,
    summary="Bulk-set amenities for a masjid",
    description="Replaces all amenities for a masjid with the provided list.",
)
def set_masjid_amenities(
    masjid_id: str,
    body: BulkAmenityRequest,
    repo: MasjidRepository = Depends(get_masjid_repo),
):
    try:
        keys = list({a.value for a in body.amenities})
        invalid = set(keys) - VALID_AMENITY_KEYS
        if invalid:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Invalid amenity keys: {sorted(invalid)}",
            )

        repo.set_amenities(masjid_id, keys)
        return success_response(
            {"masjid_id": masjid_id, "amenities": keys},
            message="Amenities updated",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error setting amenities for %s: %s", masjid_id, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update amenities: {str(e)}",
        )


@masjid_router.patch(
    ApiEndpoints.MASJID_AMENITIES.value,
    summary="Toggle a single amenity for a masjid",
    description=(
        "Adds or removes a single amenity for a masjid. "
        "Use action='add' to enable, action='remove' to disable."
    ),
)
def toggle_masjid_amenity(
    masjid_id: str,
    body: AmenityToggleRequest,
    repo: MasjidRepository = Depends(get_masjid_repo),
):
    try:
        key = body.amenity_key.value
        if key not in VALID_AMENITY_KEYS:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Invalid amenity key: {key}",
            )

        if body.action == "add":
            repo.add_amenity(masjid_id, key)
        else:
            repo.remove_amenity(masjid_id, key)

        updated = repo.get_amenities(masjid_id)
        return success_response(
            {"masjid_id": masjid_id, "amenities": updated},
            message=f"Amenity '{key}' {'added' if body.action == 'add' else 'removed'}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error toggling amenity for %s: %s", masjid_id, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle amenity: {str(e)}",
        )
