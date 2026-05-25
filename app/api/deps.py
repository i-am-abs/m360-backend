from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.modules.feature_flag.application.services.feature_flag_management_service import (
    FeatureFlagManagementService,
)
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService

bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def requireModuleService(serviceValue: Any, moduleName: str, errorCode: ErrorCode) -> Any:
    if serviceValue is None:
        raise ApiException(
            f"{moduleName} module is disabled.",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            code=errorCode,
        )
    return serviceValue


def get_quran_oauth_service(request: Request) -> QuranOAuthService:
    return requireModuleService(
        request.app.state.quran_oauth_service,
        "Quran",
        ErrorCode.QURAN_MODULE_DISABLED,
    )


def get_quran_api_client(request: Request) -> QuranApiClient:
    return requireModuleService(
        request.app.state.quran_api_client,
        "Quran",
        ErrorCode.QURAN_MODULE_DISABLED,
    )


def get_masjid_search_service(request: Request) -> MasjidSearchService:
    return requireModuleService(
        request.app.state.masjid_search_service,
        "Masjid",
        ErrorCode.MASJID_MODULE_DISABLED,
    )


def get_user_masjid_service(request: Request) -> UserMasjidService:
    return requireModuleService(
        request.app.state.user_masjid_service,
        "Masjid",
        ErrorCode.MASJID_MODULE_DISABLED,
    )


def get_feature_flag_management_service(request: Request) -> FeatureFlagManagementService:
    return requireModuleService(
        request.app.state.feature_flag_management_service,
        "Feature flag",
        ErrorCode.FEATURE_FLAG_MODULE_DISABLED,
    )


def get_phone_auth_service(request: Request) -> PhoneAuthService:
    return requireModuleService(
        request.app.state.phone_auth_service,
        "Auth",
        ErrorCode.AUTH_MODULE_DISABLED,
    )


def get_user_store(request: Request) -> UserRepository:
    return requireModuleService(
        request.app.state.user_store,
        "User persistence",
        ErrorCode.USER_PERSISTENCE_MODULE_DISABLED,
    )


def get_bearer_credentials(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> HTTPAuthorizationCredentials:
    if credentials is None or not credentials.credentials:
        raise ApiException(
            "Missing Authorization bearer token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
            code=ErrorCode.AUTH_MISSING_TOKEN,
        )
    return credentials


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
        store: UserRepository = Depends(get_user_store),
) -> Dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise ApiException(
            "Missing Authorization bearer token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
            code=ErrorCode.AUTH_MISSING_TOKEN,
        )
    user = store.getUserBySession(credentials.credentials)
    if not user:
        raise ApiException(
            "Invalid or expired access token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
            code=ErrorCode.AUTH_INVALID_TOKEN,
        )
    return user
