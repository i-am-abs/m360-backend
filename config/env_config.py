from __future__ import annotations

import os
from typing import Final

from config.env_bootstrap import DEFAULT_LAYERED_ENV_FILES, DotEnvBootstrap
from constants.paths import PROJECT_ROOT

_loaded = False
ENV: dict[str, str] = {}

_bootstrap: Final[DotEnvBootstrap] = DotEnvBootstrap(
    PROJECT_ROOT,
    DEFAULT_LAYERED_ENV_FILES,
)


def _refresh_env_map() -> None:
    ENV.clear()
    ENV.update(dict(os.environ))


def load_app_env() -> None:
    global _loaded
    if _loaded:
        return

    _bootstrap.apply()
    _refresh_env_map()
    _loaded = True


def get_env(key: str, default: str | None = None) -> str | None:
    load_app_env()
    if default is None:
        return ENV.get(key)
    return ENV.get(key, default)
