from http import HTTPStatus
from typing import Any, Dict

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.impl.oauth_token_provider import OAuthTokenProvider
from client.quran_api_client import QuranApiClient
from config.application_settings import ApplicationSettings
from exceptions.api_exception import ApiException
from modules.auth.service.phone_auth_service import PhoneAuthApplicationService
from services.google_places.contracts import MasjidPlacesService
from services.quran_oauth_facade import QuranOAuthFacade
from services.user_masjid_service import UserMasjidService
from services.user_store import UserStore

_bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> ApplicationSettings:
    return request.app.state.settings


def get_oauth_token_provider(request: Request) -> OAuthTokenProvider:
    return request.app.state.oauth_token_provider


def get_quran_oauth_facade(request: Request) -> QuranOAuthFacade:
    return QuranOAuthFacade(request.app.state.oauth_token_provider)


def get_quran_api_client(request: Request) -> QuranApiClient:
    return request.app.state.quran_api_client


def get_masjid_places_service(request: Request) -> MasjidPlacesService:
    return request.app.state.masjid_places_service


def get_user_store(request: Request) -> UserStore:
    return request.app.state.user_store


def get_phone_auth_service(request: Request) -> PhoneAuthApplicationService:
    return request.app.state.phone_auth_service


def get_user_masjid_service(request: Request) -> UserMasjidService:
    return request.app.state.user_masjid_service


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer),
        store: UserStore = Depends(get_user_store),
) -> Dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise ApiException(
            "Missing Authorization bearer token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
        )
    user = store.get_user_by_session(credentials.credentials)
    if not user:
        raise ApiException(
            "Invalid or expired access token",
            status_code=HTTPStatus.UNAUTHORIZED.value,
        )
    return user
