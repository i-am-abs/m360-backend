from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.services.broadcast_service import BroadcastService
from app.services.claim_service import ClaimService
from app.services.connection_manager import ConnectionManager
from app.services.donation_service import DonationService
from app.services.follower_service import FollowerService
from app.services.masjid_entity_service import MasjidEntityService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService

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


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), store: UserRepository = Depends(get_user_store),) -> Dict[str, Any]:
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


def get_masjid_entity_service(request: Request) -> MasjidEntityService:
    return request.app.state.masjid_entity_service


def get_claim_service(request: Request) -> ClaimService:
    return request.app.state.claim_service


def get_broadcast_service(request: Request) -> BroadcastService:
    return request.app.state.broadcast_service


def get_follower_service(request: Request) -> FollowerService:
    return request.app.state.follower_service


def get_donation_service(request: Request) -> DonationService:
    return request.app.state.donation_service


def get_connection_manager(request: Request) -> ConnectionManager:
    return request.app.state.connection_manager


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    store: UserRepository = Depends(get_user_store),
) -> Optional[Dict[str, Any]]:
    if credentials is None or not credentials.credentials:
        return None
    user = store.get_user_by_session(credentials.credentials)
    return user


def require_platform_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if current_user.get("global_role") != "platform_admin":
        raise ApiException(
            "Forbidden",
            status_code=HTTPStatus.FORBIDDEN.value,
            code=ErrorCode.FORBIDDEN,
        )
    return current_user
