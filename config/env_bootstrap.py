from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Final, Mapping


class DotEnvBootstrap:
    def __init__(
            self,
            project_root: Path,
            env_file_by_app_env: Mapping[str, str],
    ) -> None:
        self._root = project_root
        self._env_file_by_app_env = dict(env_file_by_app_env)

    def apply(self) -> None:
        from dotenv import load_dotenv

        env_path = self._root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)

        app_env = (os.getenv("APP_ENV") or "").lower()
        env_file = (
            self._env_file_by_app_env.get(app_env) if app_env else None
        )

        if not env_file:
            for _name, path in self._env_file_by_app_env.items():
                p = self._root / path
                if p.exists():
                    env_file = path
                    break
            if not env_file and env_path.exists():
                return

        if env_file:
            p = self._root / env_file
            if p.exists():
                load_dotenv(p, override=True)
        elif not env_path.exists():
            warnings.warn(
                f"Environment file {env_file or '.env'} not found. Using system env.",
                stacklevel=3,
            )


DEFAULT_LAYERED_ENV_FILES: Final[dict[str, str]] = {
    "prod": ".env.prod",
    "production": ".env.prod",
    "preprod": ".env.preprod",
    "dev": ".env.dev",
    "local": ".env.local",
}
