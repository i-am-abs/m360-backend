from fastapi import APIRouter

from app.core.config import Settings
from app.core.module_registry import buildApiV1Router, resolveModuleActivationState


def createApiV1Router(settings: Settings) -> APIRouter:
    moduleActivationState = resolveModuleActivationState(settings)
    return buildApiV1Router(moduleActivationState)


api_v1_router = APIRouter()
