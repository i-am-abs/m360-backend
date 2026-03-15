from typing import Optional

from feature_flags.city_resolver import CityResolver
from feature_flags.feature_context import FeatureContext
from feature_flags.feature_flag_provider import FeatureFlagProvider
from feature_flags.impl.config_feature_flag_provider import ConfigFeatureFlagProvider
from feature_flags.impl.google_city_resolver import GoogleCityResolver

_feature_flag_provider: Optional[FeatureFlagProvider] = None
_city_resolver: Optional[CityResolver] = None


def get_feature_flag_provider() -> FeatureFlagProvider:
    global _feature_flag_provider

    if _feature_flag_provider is None:
        _feature_flag_provider = ConfigFeatureFlagProvider()

    return _feature_flag_provider


def get_city_resolver() -> CityResolver:
    global _city_resolver

    if _city_resolver is None:
        _city_resolver = GoogleCityResolver()

    return _city_resolver


def build_context_for_masjid(
    latitude: float,
    longitude: float,
    headers: Optional[dict] = None,
) -> FeatureContext:
    city: Optional[str] = None
    headers_dict = {k: str(v) for k, v in (headers or {}).items()}
    city_header = None

    for k, v in headers_dict.items():
        if k.lower() == "x-city" and v:
            city_header = v.strip()
            break

    if city_header:
        city = city_header

    else:
        resolver = get_city_resolver()
        city = resolver.get_city(latitude, longitude)

    return FeatureContext(
        city=city,
        latitude=latitude,
        longitude=longitude,
        headers=headers_dict,
    )
