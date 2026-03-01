import os
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

from config.quran_api_config import QuranApiConfig

# Project root (parent of config/) so .env is found regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_ENV_FILES = {
    "prod": ".env.prod",
    "production": ".env.prod",
    "preprod": ".env.preprod",
    "dev": ".env.dev",
    "local": ".env.local",
}

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


def _load_env() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    app_env = (os.getenv("APP_ENV") or "").lower()
    env_file = _ENV_FILES.get(app_env) if app_env else None

    if not env_file:
        for _name, path in _ENV_FILES.items():
            p = _PROJECT_ROOT / path
            if p.exists():
                env_file = path
                break
        if not env_file and env_path.exists():
            return

    if env_file:
        p = _PROJECT_ROOT / env_file
        if p.exists():
            load_dotenv(p, override=True)
    elif not env_path.exists():
        import warnings
        warnings.warn(
            f"Environment file {env_file or '.env'} not found. Using system env."
        )


def _credentials() -> Tuple[str, str]:
    client_id = os.getenv("QURAN_CLIENT_ID") or os.getenv("QF_CLIENT_ID")
    client_secret = os.getenv("QURAN_CLIENT_SECRET") or os.getenv("QF_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Quran Foundation API credentials. "
            "Request access: https://api-docs.quran.foundation/request-access"
        )
    return client_id, client_secret


def _base_urls() -> Tuple[str, str]:
    qf_env = (os.getenv("QF_ENV") or os.getenv("APP_ENV") or "prelive").lower()
    base_url, oauth_url = _QF_BASE_URLS.get(qf_env, _QF_BASE_URLS["prelive"])

    base_url = (os.getenv("QURAN_BASE_URL") or base_url).strip().rstrip("/")
    if base_url.endswith("/content/api"):
        base_url = base_url[: -len("/content/api")]
    oauth_url = (os.getenv("QURAN_OAUTH_URL") or oauth_url).strip().rstrip("/")

    if not base_url or not base_url.startswith(("http://", "https://")):
        raise ValueError(
            f"Invalid QURAN_BASE_URL (must be a full URL). Got: {base_url!r}"
        )
    if not oauth_url or not oauth_url.startswith(("http://", "https://")):
        raise ValueError(
            f"Invalid QURAN_OAUTH_URL (must be a full URL). Got: {oauth_url!r}"
        )
    return base_url, oauth_url


def create_config() -> QuranApiConfig:
    _load_env()
    client_id, client_secret = _credentials()
    base_url, oauth_url = _base_urls()
    return QuranApiConfig(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        oauth_url=oauth_url,
    )
