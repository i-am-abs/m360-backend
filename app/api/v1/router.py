from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_api,
    admins,
    auth,
    broadcast,
    broadcasts,
    claims,
    donations,
    fcm,
    features,
    health,
    internal,
    masjid,
    masjid_content,
    msg91_webhook,
    mux_webhook,
    quran,
    upload,
    uploads,
    verification_requests,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(msg91_webhook.router)
api_v1_router.include_router(quran.router)
# Registered before masjid.router: routes match in order, so the literal
# /masjids/tab must be declared ahead of /masjids/{masjid_id}.
api_v1_router.include_router(features.router)
api_v1_router.include_router(masjid.router)
api_v1_router.include_router(masjid_content.router)
api_v1_router.include_router(admins.router)
api_v1_router.include_router(verification_requests.router)
api_v1_router.include_router(uploads.router)
api_v1_router.include_router(internal.router)
api_v1_router.include_router(fcm.router)
api_v1_router.include_router(broadcasts.router)
api_v1_router.include_router(claims.router)
api_v1_router.include_router(broadcast.router)
api_v1_router.include_router(donations.router)
api_v1_router.include_router(upload.router)
api_v1_router.include_router(mux_webhook.router)
api_v1_router.include_router(admin_api.router)
