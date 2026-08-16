from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from app.core.enums.masjid_amenity import Amenity


def empty_amenity_status() -> Dict[str, Optional[bool]]:
    return {key: None for key in Amenity.values()}


def infer_amenities_from_google(place: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """Map Google Places parking/accessibility flags onto our amenity keys."""
    if not isinstance(place, dict):
        return {}

    parking = place.get("parkingOptions") or {}
    accessibility = place.get("accessibilityOptions") or {}
    inferred: Dict[str, bool] = {}

    if any(
            parking.get(flag) is True
            for flag in (
                    "freeParkingLot",
                    "paidParkingLot",
                    "freeGarageParking",
                    "paidGarageParking",
                    "freeStreetParking",
                    "paidStreetParking",
                    "valetParking",
            )
    ):
        inferred[Amenity.CAR_PARKING.value] = True

    if accessibility.get("wheelchairAccessibleEntrance") is True:
        inferred[Amenity.WHEELCHAIR_ACCESS.value] = True
    if accessibility.get("wheelchairAccessibleParking") is True:
        inferred[Amenity.CAR_PARKING.value] = True
        inferred[Amenity.WHEELCHAIR_ACCESS.value] = True

    return inferred


def facilities_from_google(place: Optional[Dict[str, Any]]) -> Dict[str, Optional[bool]]:
    if not isinstance(place, dict):
        place = {}
    accessibility = place.get("accessibilityOptions") or {}
    parking = place.get("parkingOptions") or {}
    payment = place.get("paymentOptions") or {}
    return {
        "wheelchair_accessible_entrance": _tri(accessibility.get("wheelchairAccessibleEntrance")),
        "wheelchair_accessible_parking": _tri(accessibility.get("wheelchairAccessibleParking")),
        "restroom": _tri(place.get("restroom")),
        "free_parking_lot": _tri(parking.get("freeParkingLot")),
        "paid_parking_lot": _tri(parking.get("paidParkingLot")),
        "accepts_nfc": _tri(payment.get("acceptsNfc")),
    }


def build_amenity_status(
        stored: Optional[Iterable[str]] = None,
        place: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[bool]]:
    """Every system amenity, for UI enable/disable.

    true  — saved on the masjid or known from Google Places
    null  — unknown (UI shows the icon disabled)
    """
    status = empty_amenity_status()
    for key, enabled in infer_amenities_from_google(place).items():
        if key in status and enabled:
            status[key] = True
    for key in stored or []:
        if key in status:
            status[key] = True
    return status


def enabled_amenity_keys(status: Dict[str, Optional[bool]]) -> list[str]:
    return [key for key, value in status.items() if value is True]


def apply_amenity_fields(
        place: Dict[str, Any],
        stored: Optional[Iterable[str]] = None,
) -> None:
    """Keep listing fields; add amenity list + full status map."""
    status = build_amenity_status(stored, place)
    place["amenityStatus"] = status
    place["amenities"] = enabled_amenity_keys(status)
    place["facilities"] = facilities_from_google(place)
    meters = place.get("distanceMeters")
    if meters is not None:
        try:
            place["distanceKm"] = round(float(meters) / 1000.0, 1)
        except (TypeError, ValueError):
            place["distanceKm"] = None


def _tri(value: Any) -> Optional[bool]:
    if value is True:
        return True
    if value is False:
        return False
    return None
