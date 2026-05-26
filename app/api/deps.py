from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.exceptions.base import ApiException
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.modules.feature_flag.application.services.feature_flag_management_service import FeatureFlagManagementService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService

bearer = HTTPBearer(auto_error=False)


class DependsSettings:
    def get_settings(self, request: Request) -> Settings:
        return request.app.state.settings

    def requireModuleService(self, serviceValue: Any, moduleName: str, errorCode: str) -> Any:
        if serviceValue is None:
            raise ApiException(
                f"{moduleName} module is disabled.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                code=errorCode,
            )
        return serviceValue

    def get_quran_oauth_service(self, request: Request) -> QuranOAuthService:
        return self.requireModuleService(
            request.app.state.quran_oauth_service,
            "Quran",
            "QURAN_MODULE_DISABLED",
        )

    def get_quran_api_client(self, request: Request) -> QuranApiClient:
        return self.requireModuleService(
            request.app.state.quran_api_client,
            "Quran",
            "QURAN_MODULE_DISABLED",
        )

    def get_masjid_search_service(self, request: Request) -> MasjidSearchService:
        return self.requireModuleService(
            request.app.state.masjid_search_service,
            "Masjid",
            "MASJID_MODULE_DISABLED",
        )

    def get_user_masjid_service(self, request: Request) -> UserMasjidService:
        return self.requireModuleService(
            request.app.state.user_masjid_service,
            "Masjid",
            "MASJID_MODULE_DISABLED",
        )

    def get_feature_flag_management_service(self, request: Request) -> FeatureFlagManagementService:
        return self.requireModuleService(
            request.app.state.feature_flag_management_service,
            "Feature flag",
            "FEATURE_FLAG_MODULE_DISABLED",
        )

    def get_phone_auth_service(self, request: Request) -> PhoneAuthService:
        return self.requireModuleService(
            request.app.state.phone_auth_service,
            "Auth",
            "AUTH_MODULE_DISABLED",
        )

    def get_user_store(self, request: Request) -> UserRepository:
        return self.requireModuleService(
            request.app.state.user_store,
            "User persistence",
            "USER_PERSISTENCE_MODULE_DISABLED",
        )

    def get_bearer_credentials(self, credentials: HTTPAuthorizationCredentials = Depends(
        bearer)) -> HTTPAuthorizationCredentials:
        if credentials is None or not credentials.credentials:
            raise ApiException(
                "Missing Authorization bearer token",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code="AUTH_MISSING_TOKEN",
            )
        return credentials

    def get_current_user(self, credentials: HTTPAuthorizationCredentials, store: UserRepository) -> Dict[str, Any]:
        if credentials is None or not credentials.credentials:
            raise ApiException(
                "Missing Authorization bearer token",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code="AUTH_MISSING_TOKEN",
            )
        user = store.getUserBySession(credentials.credentials)
        if not user:
            raise ApiException(
                "Invalid or expired access token",
                status_code=HTTPStatus.UNAUTHORIZED.value,
                code="AUTH_INVALID_TOKEN",
            )
        return user


_depends_settings = DependsSettings()

get_settings = _depends_settings.get_settings
get_quran_oauth_service = _depends_settings.get_quran_oauth_service
get_quran_api_client = _depends_settings.get_quran_api_client
get_masjid_search_service = _depends_settings.get_masjid_search_service
get_user_masjid_service = _depends_settings.get_user_masjid_service
get_feature_flag_management_service = _depends_settings.get_feature_flag_management_service
get_phone_auth_service = _depends_settings.get_phone_auth_service
get_user_store = _depends_settings.get_user_store
get_bearer_credentials = _depends_settings.get_bearer_credentials


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(get_bearer_credentials),
        store: UserRepository = Depends(get_user_store),
) -> Dict[str, Any]:
    return _depends_settings.get_current_user(credentials, store)
