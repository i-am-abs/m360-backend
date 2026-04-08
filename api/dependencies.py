from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from client.quran_api_client import QuranApiClient
from config.factory.quran_config_factory import create_config
from exceptions.api_exception import ApiException
from services.google_places.contracts import MasjidPlacesService
from services.google_places.provider import (
    get_masjid_places_service as _masjid_singleton,
)
from services.phone_auth_service import Msg91PhoneAuthService
from services.user_masjid_service import UserMasjidService
from services.user_store import UserStore

_quran_client: Optional[QuranApiClient] = None
_user_store: Optional[UserStore] = None
_phone_auth_service: Optional[Msg91PhoneAuthService] = None
_user_masjid_service: Optional[UserMasjidService] = None
_bearer = HTTPBearer(auto_error=False)


def get_quran_api_client() -> QuranApiClient:
    global _quran_client
    if _quran_client is None:
        _quran_client = QuranApiClient(create_config())
    return _quran_client


def get_masjid_places_service() -> MasjidPlacesService:
    return _masjid_singleton()


def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store


def get_phone_auth_service() -> Msg91PhoneAuthService:
    global _phone_auth_service
    if _phone_auth_service is None:
        _phone_auth_service = Msg91PhoneAuthService(get_user_store())
    return _phone_auth_service


def get_user_masjid_service() -> UserMasjidService:
    global _user_masjid_service
    if _user_masjid_service is None:
        _user_masjid_service = UserMasjidService(
            store=get_user_store(),
            masjid_places_service=get_masjid_places_service(),
        )
    return _user_masjid_service


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
