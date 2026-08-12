from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.utils.geo import haversine_meters

_KM_PER_DEGREE_LAT = 111.32

# Sorts after every real shape so shapeless documents never win a tie-break.
_UNBOUNDED_AREA_KM2 = float("inf")

RegionDoc = Dict[str, Any]


def _as_float(value: Any) -> Optional[float]:
    # bool is an int subclass; float(True) == 1.0 would silently pass as a coordinate.
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_name(value: Any) -> str:
    """Fold a place name so 'Uttar Pradesh', 'uttar-pradesh' and 'UttarPradesh' unify."""
    if value is None:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def circle_of(doc: RegionDoc) -> Optional[Tuple[float, float, float]]:
    """Return (latitude, longitude, radius_km) when the document defines a circle."""
    center = doc.get("center")
    if not isinstance(center, dict):
        return None
    latitude = _as_float(center.get("latitude"))
    longitude = _as_float(center.get("longitude"))
    radius_km = _as_float(doc.get("radius_km"))
    if latitude is None or longitude is None or radius_km is None:
        return None
    if radius_km <= 0:
        return None
    return latitude, longitude, radius_km


def rectangle_of(doc: RegionDoc) -> Optional[Tuple[float, float, float, float]]:
    """Return (lat_min, lat_max, lng_min, lng_max) when the document defines a box."""
    bounds = doc.get("bounds")
    if not isinstance(bounds, dict):
        return None
    lat_min = _as_float(bounds.get("lat_min"))
    lat_max = _as_float(bounds.get("lat_max"))
    lng_min = _as_float(bounds.get("lng_min"))
    lng_max = _as_float(bounds.get("lng_max"))
    if None in (lat_min, lat_max, lng_min, lng_max):
        return None
    if lat_min > lat_max or lng_min > lng_max:
        return None
    return lat_min, lat_max, lng_min, lng_max


def covers_point(doc: RegionDoc, latitude: float, longitude: float) -> bool:
    """A circle takes precedence so a document never declares two conflicting shapes."""
    circle = circle_of(doc)
    if circle is not None:
        center_lat, center_lng, radius_km = circle
        distance_km = haversine_meters(
            center_lat, center_lng, latitude, longitude,
        ) / 1000.0
        return distance_km <= radius_km

    rectangle = rectangle_of(doc)
    if rectangle is not None:
        lat_min, lat_max, lng_min, lng_max = rectangle
        return lat_min <= latitude <= lat_max and lng_min <= longitude <= lng_max

    return False


def coverage_area_km2(doc: RegionDoc) -> float:
    """Approximate footprint, used to prefer the tightest region covering a point."""
    circle = circle_of(doc)
    if circle is not None:
        _, _, radius_km = circle
        return math.pi * radius_km * radius_km

    rectangle = rectangle_of(doc)
    if rectangle is not None:
        lat_min, lat_max, lng_min, lng_max = rectangle
        mean_lat = math.radians((lat_min + lat_max) / 2.0)
        height_km = (lat_max - lat_min) * _KM_PER_DEGREE_LAT
        width_km = (lng_max - lng_min) * _KM_PER_DEGREE_LAT * math.cos(mean_lat)
        return abs(height_km * width_km)

    return _UNBOUNDED_AREA_KM2


def _priority_of(doc: RegionDoc) -> float:
    priority = _as_float(doc.get("priority"))
    return priority if priority is not None else 0.0


def specificity_key(doc: RegionDoc) -> Tuple[float, float, str]:
    """Ordering for overlapping regions: highest priority, then tightest, then stable.

    The trailing location_key keeps the winner identical across requests when two
    regions are otherwise indistinguishable, which a raw Mongo sort does not promise.
    """
    return (
        -_priority_of(doc),
        coverage_area_km2(doc),
        str(doc.get("location_key") or ""),
    )


def best_match(docs: Iterable[RegionDoc]) -> Optional[RegionDoc]:
    candidates = list(docs)
    if not candidates:
        return None
    return min(candidates, key=specificity_key)


def best_coordinate_match(
        docs: Iterable[RegionDoc],
        latitude: float,
        longitude: float,
) -> Optional[RegionDoc]:
    return best_match(
        doc for doc in docs if covers_point(doc, latitude, longitude)
    )


def _field_values(doc: RegionDoc, field: str) -> set:
    """Normalized accepted spellings for country/state/city, including aliases."""
    values = set()
    primary = normalize_name(doc.get(field))
    if primary:
        values.add(primary)

    aliases = doc.get("aliases")
    if isinstance(aliases, dict):
        for alias in aliases.get(field) or []:
            normalized = normalize_name(alias)
            if normalized:
                values.add(normalized)
    return values


def region_matches(
        doc: RegionDoc,
        *,
        country: Optional[str],
        state: Optional[str],
        city: Optional[str],
) -> bool:
    """Exact tier match: a None expectation requires the document to be silent too."""
    for field, expected in (
            ("country", country),
            ("state", state),
            ("city", city),
    ):
        values = _field_values(doc, field)
        if expected is None:
            if values:
                return False
            continue
        if normalize_name(expected) not in values:
            return False
    return True


def region_tiers(
        country: Optional[str],
        state: Optional[str],
        city: Optional[str],
) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """Most specific first: city, then state, then country."""
    tiers: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []
    if country and state and city:
        tiers.append((country, state, city))
    if country and state:
        tiers.append((country, state, None))
    if country:
        tiers.append((country, None, None))
    return tiers


def best_region_match(
        docs: Iterable[RegionDoc],
        country: Optional[str],
        state: Optional[str],
        city: Optional[str],
) -> Optional[RegionDoc]:
    candidates = list(docs)
    for tier_country, tier_state, tier_city in region_tiers(country, state, city):
        matched = best_match(
            doc for doc in candidates
            if region_matches(
                doc,
                country=tier_country,
                state=tier_state,
                city=tier_city,
            )
        )
        if matched is not None:
            return matched
    return None
