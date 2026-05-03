from fastapi import FastAPI

from auth.impl.oauth_token_provider import OAuthTokenProvider
from client.quran_api_client import QuranApiClient
from config.application_settings import ApplicationSettings
from modules.auth.domain.validators import IndiaPhoneNumberValidator
from modules.auth.gateway.msg91_gateway import Msg91OtpGateway
from modules.auth.service.phone_auth_service import PhoneAuthApplicationService
from services.google_places.masjid_places_factory import (
    create_masjid_places_service as build_masjid_places_service,
)
from services.user_masjid_service import UserMasjidService
from services.user_store import UserStore


def bootstrap_app_container(app: FastAPI) -> None:
    settings = ApplicationSettings.build()

    if settings.quran_config is not None:
        token_provider = OAuthTokenProvider(settings.quran_config)
        quran_client = QuranApiClient(settings.quran_config, token_provider)
    else:
        token_provider = None
        quran_client = None

    masjid_svc = build_masjid_places_service(settings.masjid)
    msg91 = Msg91OtpGateway(settings.msg91)
    phone_validator = IndiaPhoneNumberValidator(settings.msg91.country_code)
    user_store = UserStore(settings.persistence.user_store_file)
    phone_auth = PhoneAuthApplicationService(
        store=user_store,
        otp_gateway=msg91,
        phone_validator=phone_validator,
        widget_id=settings.msg91.widget_id,
        session_ttl_seconds_raw=settings.phone_auth.session_ttl_seconds_raw,
    )
    user_masjid = UserMasjidService(
        store=user_store,
        masjid_places_service=masjid_svc,
    )

    app.state.settings = settings
    app.state.oauth_token_provider = token_provider
    app.state.quran_api_client = quran_client
    app.state.masjid_places_service = masjid_svc
    app.state.user_store = user_store
    app.state.phone_auth_service = phone_auth
    app.state.user_masjid_service = user_masjid
