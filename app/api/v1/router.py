from fastapi import APIRouter

from app.api.v1.endpoints import (
    admins,
    auth,
    features,
    health,
    internal,
    masjid,
    masjid_content,
    msg91_webhook,
    quran,
    uploads,
    verification_requests,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(msg91_webhook.router)
api_v1_router.include_router(quran.router)
api_v1_router.include_router(masjid.router)
api_v1_router.include_router(masjid_content.router)
api_v1_router.include_router(features.router)
api_v1_router.include_router(admins.router)
api_v1_router.include_router(verification_requests.router)
api_v1_router.include_router(uploads.router)
api_v1_router.include_router(internal.router)
