from __future__ import annotations

from dataclasses import dataclass
from typing import List
from app.api.v1.endpoints import auth, feature_flags, health, masjid, msg91_webhook, quran
from fastapi import APIRouter, FastAPI

from app.core.config import Settings


@dataclass(frozen=True)
class ModuleActivationState:
    quranModuleActive: bool
    masjidModuleActive: bool
    authModuleActive: bool
    msg91WebhookModuleActive: bool
    featureFlagModuleActive: bool
    redisCacheModuleActive: bool
    mongodbModuleActive: bool
    userPersistenceModuleActive: bool

    def activeModuleNames(self) -> List[str]:
        activeModules: List[str] = ["health"]
        if self.authModuleActive:
            activeModules.append("auth")

        if self.msg91WebhookModuleActive:
            activeModules.append("msg91_webhook")

        if self.quranModuleActive:
            activeModules.append("quran")
        if self.masjidModuleActive:
            activeModules.append("masjid")

        if self.featureFlagModuleActive:
            activeModules.append("feature_flags")
        return activeModules


def resolveModuleActivationState(settings: Settings) -> ModuleActivationState:
    authModuleActive = settings.auth_module_active
    masjidModuleActive = settings.masjid_module_active
    return ModuleActivationState(
        quranModuleActive=settings.quran_module_active,
        masjidModuleActive=masjidModuleActive,
        authModuleActive=authModuleActive,
        msg91WebhookModuleActive=settings.msg91_webhook_module_active and authModuleActive,
        featureFlagModuleActive=settings.feature_flag_module_active,
        redisCacheModuleActive=settings.redis_cache_module_active,
        mongodbModuleActive=settings.mongodb_configured,
        userPersistenceModuleActive=authModuleActive or masjidModuleActive,
    )


def buildApiV1Router(moduleActivationState: ModuleActivationState) -> APIRouter:
    apiRouter = APIRouter()
    apiRouter.include_router(health.router)

    if moduleActivationState.authModuleActive:
        apiRouter.include_router(auth.router)

    if moduleActivationState.msg91WebhookModuleActive:
        apiRouter.include_router(msg91_webhook.router)

    if moduleActivationState.quranModuleActive:
        apiRouter.include_router(quran.router)

    if moduleActivationState.masjidModuleActive:
        apiRouter.include_router(masjid.router)

    if moduleActivationState.featureFlagModuleActive:
        apiRouter.include_router(feature_flags.router)
    return apiRouter


def attachEnabledModulesToAppState(app: FastAPI, moduleActivationState: ModuleActivationState) -> None:
    app.state.module_activation_state = moduleActivationState
