from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.services.admin_service import AdminService
from app.services.broadcast_service import BroadcastService
from app.services.feature_flag_service import FeatureFlagService
from app.services.internal_timings_service import InternalTimingsService
from app.services.masjid_amenities_service import MasjidAmenitiesService
from app.services.masjid_listing_service import MasjidListingService
from app.services.masjid_timings_service import MasjidTimingsService
from app.services.notification_service import NotificationService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.upload_service import UploadService
from app.services.user_masjid_service import UserMasjidService
from app.services.verification_service import VerificationService

bearer = HTTPBearer(auto_error=False)

QURAN_NOT_CONFIGURED = (
    "Quran Foundation API is not configured. "
    "Set QURAN_CLIENT_ID and QURAN_CLIENT_SECRET."
)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_quran_oauth_service(request: Request) -> QuranOAuthService:
    svc = request.app.state.quran_oauth_service
    if svc is None:
        raise ApiException(
            QURAN_NOT_CONFIGURED,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            code=ErrorCode.QURAN_API_NOT_CONFIGURED,
        )
    return svc


def get_quran_api_client(request: Request) -> QuranApiClient:
    client = request.app.state.quran_api_client
    if client is None:
        raise ApiException(
            QURAN_NOT_CONFIGURED,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            code=ErrorCode.QURAN_API_NOT_CONFIGURED,
        )
    return client


def get_masjid_search_service(request: Request) -> MasjidSearchService:
    return request.app.state.masjid_search_service


def get_user_masjid_service(request: Request) -> UserMasjidService:
    return request.app.state.user_masjid_service


def get_phone_auth_service(request: Request) -> PhoneAuthService:
    return request.app.state.phone_auth_service


def get_user_store(request: Request) -> UserRepository:
    return request.app.state.user_store


def get_masjid_store(request: Request) -> MasjidRepository:
    return request.app.state.masjid_store


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


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer),
                     store: UserRepository = Depends(get_user_store), ) -> Dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise ApiException(
            "Missing Authorization bearer token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
            code=ErrorCode.AUTH_MISSING_TOKEN,
        )
    user = store.get_user_by_session(credentials.credentials)
    if not user:
        raise ApiException(
            "Invalid or expired access token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
            code=ErrorCode.AUTH_INVALID_TOKEN,
        )
    return user


def get_optional_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
        store: UserRepository = Depends(get_user_store),
) -> Optional[Dict[str, Any]]:
    if credentials is None or not credentials.credentials:
        return None
    return store.get_user_by_session(credentials.credentials)


def get_feature_flag_service(request: Request) -> FeatureFlagService:
    return request.app.state.feature_flag_service


def get_admin_service(request: Request) -> AdminService:
    return request.app.state.admin_service


def get_verification_service(request: Request) -> VerificationService:
    return request.app.state.verification_service


def get_upload_service(request: Request) -> UploadService:
    return request.app.state.upload_service


def get_masjid_listing_service(request: Request) -> MasjidListingService:
    return request.app.state.masjid_listing_service


def get_masjid_timings_service(request: Request) -> MasjidTimingsService:
    return request.app.state.masjid_timings_service


def get_masjid_amenities_service(request: Request) -> MasjidAmenitiesService:
    return request.app.state.masjid_amenities_service


def get_internal_timings_service(request: Request) -> InternalTimingsService:
    return request.app.state.internal_timings_service


def get_notification_service(request: Request) -> NotificationService:
    return request.app.state.notification_service


def get_broadcast_service(request: Request) -> BroadcastService:
    return request.app.state.broadcast_service


def verify_internal_api_key(
        request: Request,
        x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-Api-Key"),
) -> None:
    settings: Settings = request.app.state.settings
    if not settings.internal_api_configured:
        raise ApiException(
            "Internal API is not configured",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            code=ErrorCode.CONFIG_MISSING,
        )
    if not x_internal_api_key or x_internal_api_key != settings.internal_api_key:
        raise ApiException(
            "Invalid internal API key",
            status_code=HTTPStatus.UNAUTHORIZED.value,
            code=ErrorCode.AUTH_INTERNAL_KEY_INVALID,
        )
