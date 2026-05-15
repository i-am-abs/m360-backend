from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, masjid, msg91_webhook, quran

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(msg91_webhook.router)
api_v1_router.include_router(quran.router)
api_v1_router.include_router(masjid.router)
