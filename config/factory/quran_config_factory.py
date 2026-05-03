from typing import Mapping, Tuple

from config.env_config import ENV, load_app_env
from config.quran_api_config import QuranApiConfig
from constants.env_keys import EnvKeys

_QF_BASE_URLS = {
    "production": (
        "https://apis.quran.foundation",
        "https://oauth2.quran.foundation",
    ),
    "prod": (
        "https://apis.quran.foundation",
        "https://oauth2.quran.foundation",
    ),
    "prelive": (
        "https://apis-prelive.quran.foundation",
        "https://prelive-oauth2.quran.foundation",
    ),
}


def _credentials(env: Mapping[str, str]) -> Tuple[str, str]:
    client_id = env.get(EnvKeys.QURAN_CLIENT_ID.value) or env.get(
        EnvKeys.QF_CLIENT_ID.value
    )
    client_secret = env.get(EnvKeys.QURAN_CLIENT_SECRET.value) or env.get(
        EnvKeys.QF_CLIENT_SECRET.value
    )
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Quran Foundation API credentials. "
            "Request access: https://api-docs.quran.foundation/request-access"
        )
    return client_id, client_secret


def _base_urls(env: Mapping[str, str]) -> Tuple[str, str]:
    qf_env = (
            env.get(EnvKeys.QF_ENV.value)
            or env.get(EnvKeys.APP_ENV.value)
            or "prelive"
    ).lower()
    base_url, oauth_url = _QF_BASE_URLS.get(qf_env, _QF_BASE_URLS["prelive"])

    base_url = (
            env.get(EnvKeys.QURAN_BASE_URL.value) or base_url
    ).strip().rstrip("/")
    if base_url.endswith("/content/api"):
        base_url = base_url[: -len("/content/api")]
    oauth_url = (
            env.get(EnvKeys.QURAN_OAUTH_URL.value) or oauth_url
    ).strip().rstrip("/")

    if not base_url or not base_url.startswith(("http://", "https://")):
        raise ValueError(
            f"Invalid QURAN_BASE_URL (must be a full URL). Got: {base_url!r}"
        )
    if not oauth_url or not oauth_url.startswith(("http://", "https://")):
        raise ValueError(
            f"Invalid QURAN_OAUTH_URL (must be a full URL). Got: {oauth_url!r}"
        )
    return base_url, oauth_url


def create_quran_api_config(env: Mapping[str, str]) -> QuranApiConfig:
    client_id, client_secret = _credentials(env)
    base_url, oauth_url = _base_urls(env)
    return QuranApiConfig(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        oauth_url=oauth_url,
    )


def create_config() -> QuranApiConfig:
    load_app_env()
    return create_quran_api_config(ENV)
