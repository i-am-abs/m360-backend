from __future__ import annotations

from fastapi import FastAPI
from pymongo import MongoClient

from app.core.config import Settings
from app.core.logging import get_logger

from app.gateways.http_client import HttpxClient
from app.gateways.msg91_gateway import Msg91OtpGateway
from app.gateways.oauth_token_provider import OAuthTokenProvider
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.token_provider import TokenProvider
from app.interfaces.user_repository import UserRepository
from app.repositories.google_places_client import GooglePlacesClient
from app.repositories.local_cache_user_store import LocalCacheUserStore
from app.repositories.mongo_user_store import MongoUserStore
from app.services.masjid_search_service import GoogleMasjidSearchService
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran.client import QuranApiClient
from app.services.quran_oauth_service import QuranOAuthService
from app.services.user_masjid_service import UserMasjidService
from app.utils.phone import IndiaPhoneValidator

_log = get_logger(__name__)


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


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


def _create_user_repository(app: FastAPI, settings: Settings) -> UserRepository:
    if settings.mongodb_enabled:
        if not settings.mongodb_uri or not str(settings.mongodb_uri).strip():
            raise RuntimeError(
                "MONGODB_URI is required when MONGODB_ENABLED (or MONGODB) is true."
            )
        client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=10_000,
        )
        try:
            client.admin.command("ping")
        except Exception as e:
            client.close()
            raise RuntimeError(
                "MongoDB ping failed — check MONGODB_URI, credentials, and firewall "
                "(e.g. GCP allowlist for Atlas / self-hosted port 27017)."
            ) from e
        app.state.mongo_client = client
        return MongoUserStore(client.get_database(settings.mongodb_database))
    app.state.mongo_client = None
    return LocalCacheUserStore()


def _create_phone_auth_service(
        settings: Settings,
        user_store: UserRepository,
) -> PhoneAuthService:
    return PhoneAuthService(
        store=user_store,
        otp_gateway=Msg91OtpGateway(settings),
        phone_validator=IndiaPhoneValidator(settings.msg91_country_code),
        session_ttl_seconds=settings.auth_session_ttl_seconds,
    )


def bootstrap(app: FastAPI, settings: Settings) -> None:
    app.state.settings = settings
    _log.info(
        "MSG91 config loaded widget_id=%s country_code=%s widget_token=%s",
        settings.msg91_widget_id or "",
        settings.msg91_country_code,
        _mask_secret((settings.msg91_widget_auth_token or "").strip()),
    )

    quran_client, quran_oauth = _create_quran_components(settings)
    app.state.quran_api_client = quran_client
    app.state.quran_oauth_service = quran_oauth

    masjid_search = _create_masjid_search_service(settings)
    app.state.masjid_search_service = masjid_search

    user_store = _create_user_repository(app, settings)
    app.state.user_store = user_store

    app.state.phone_auth_service = _create_phone_auth_service(settings, user_store)

    app.state.user_masjid_service = UserMasjidService(
        store=user_store,
        places_reader=masjid_search,
    )

    mode = "mongodb" if settings.mongodb_enabled else "local_cache"
    _log.info("Bootstrap complete — persistence=%s — all services wired.", mode)
