import os
from http import HTTPStatus
from typing import Optional, Type, TypeVar, Union

from dotenv import load_dotenv

from constants.paths import PROJECT_ROOT
from exceptions.api_exception import ApiException

T = TypeVar("T", str, int)


def load_project_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def require_env(key: str, *, cast: Type[T] = str) -> T:
    load_project_dotenv()
    raw = os.getenv(key, "").strip()
    if not raw:
        raise ApiException(
            f"{key} is not configured",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        )
    try:
        return cast(raw)
    except (TypeError, ValueError):
        raise ApiException(
            f"{key} must be a valid {cast.__name__}",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        )


def get_env_optional(
    key: str,
    default: Union[str, int, None] = None,
    *,
    cast: Type[T] = str,
) -> Optional[T]:
    load_project_dotenv()
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default
