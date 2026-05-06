from __future__ import annotations

from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import get_logger
from app.gateways.http_client import HttpxClient
from app.gateways.msg91_gateway import Msg91OtpGateway
from app.gateways.oauth_token_provider import OAuthTokenProvider
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.token_provider import TokenProvider
from app.repositories.google_places_client import GooglePlacesClient
from app.repositories.user_store import JsonFileUserStore
from app.services.masjid_search_service import GoogleMasjidSearchService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService
from app.utils.phone import IndiaPhoneValidator

_log = get_logger(__name__)


def _create_quran_components(
        settings: Settings,
) -> tuple:
    if not settings.quran_api_configured:
        _log.warning(
            "Quran API disabled — set QURAN_CLIENT_ID and QURAN_CLIENT_SECRET."
        )
        return None, None

    provider: TokenProvider = OAuthTokenProvider(settings)
    http_client = HttpxClient(timeout=settings.request_timeout_seconds)
    client = QuranApiClient(settings, provider, http_client)
    oauth_service = QuranOAuthService(provider)
    return client, oauth_service


def _create_masjid_search_service(settings: Settings) -> MasjidSearchService:
    places_client = GooglePlacesClient(
        api_key=settings.google_places_api_key or "",
        timeout=settings.request_timeout_seconds,
    )
    return GoogleMasjidSearchService(places_client)


def _create_phone_auth_service(
        settings: Settings,
        user_store: JsonFileUserStore,
) -> PhoneAuthService:
    return PhoneAuthService(
        store=user_store,
        otp_gateway=Msg91OtpGateway(settings),
        phone_validator=IndiaPhoneValidator(settings.msg91_country_code),
        widget_id=settings.msg91_widget_id or "",
        session_ttl_seconds=settings.auth_session_ttl_seconds,
    )


def bootstrap(app: FastAPI, settings: Settings) -> None:
    app.state.settings = settings

    quran_client, quran_oauth = _create_quran_components(settings)
    app.state.quran_api_client = quran_client
    app.state.quran_oauth_service = quran_oauth

    masjid_search = _create_masjid_search_service(settings)
    app.state.masjid_search_service = masjid_search

    user_store = JsonFileUserStore(settings.user_store_file)
    app.state.user_store = user_store

    app.state.phone_auth_service = _create_phone_auth_service(settings, user_store)

    app.state.user_masjid_service = UserMasjidService(
        store=user_store,
        places_reader=masjid_search,
    )

    _log.info("Bootstrap complete — all services wired.")
