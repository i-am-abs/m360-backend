from fastapi import APIRouter

from app.api.v1.endpoints import admin_api, auth, broadcast, claims, donations, health, masjid, msg91_webhook, mux_webhook, quran, upload

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(msg91_webhook.router)
api_v1_router.include_router(quran.router)
api_v1_router.include_router(masjid.router)
api_v1_router.include_router(claims.router)
api_v1_router.include_router(broadcast.router)
api_v1_router.include_router(donations.router)
api_v1_router.include_router(upload.router)
api_v1_router.include_router(mux_webhook.router)
api_v1_router.include_router(admin_api.router)
