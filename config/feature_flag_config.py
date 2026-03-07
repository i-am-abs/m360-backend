import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    _load_env()
    value = os.getenv(key)
    return value.strip() if value else default


def load_feature_flags_from_file() -> Dict[str, Any]:
    _load_env()
    config_dir = _PROJECT_ROOT / "config"
    for name in ("feature_flags.yaml", "feature_flags.yml", "feature_flags.json"):
        path = config_dir / name
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            if name.endswith(".json"):
                import json

                data = json.load(f)
            else:
                data = yaml.safe_load(f) or {}
        root = data.get("feature_flags") or data
        if isinstance(root, dict):
            return root
        return {}
    return {}


def get_flag_config_from_env(flag_name: str) -> Dict[str, Any]:
    key_enabled = f"FEATURE_{flag_name.upper().replace('-', '_')}_ENABLED"
    key_cities = f"{flag_name.upper().replace('-', '_')}_CITIES"

    overrides: Dict[str, Any] = {}
    enabled_val = _get_env(key_enabled)

    if enabled_val is not None:
        overrides["enabled"] = enabled_val.lower() in ("true", "1", "yes")

    cities_val = _get_env(key_cities)

    if cities_val is not None:
        overrides["enabled_cities"] = [
            c.strip() for c in cities_val.split(",") if c.strip()
        ]
    return overrides


def normalize_city_for_comparison(city: Optional[str]) -> Optional[str]:
    if not city:
        return None
    return city.strip().lower()
