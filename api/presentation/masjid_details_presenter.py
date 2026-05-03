from typing import Any, Dict


def masjid_details_view(place: Dict[str, Any]) -> Dict[str, Any]:
    accessibility = place.get("accessibilityOptions") or {}
    parking = place.get("parkingOptions") or {}
    payment = place.get("paymentOptions") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "address": place.get("formattedAddress"),
        "location": place.get("location"),
        "timings": {
            "current_opening_hours": place.get("currentOpeningHours"),
            "regular_opening_hours": place.get("regularOpeningHours"),
        },
        "management": {
            "phone_number": place.get("internationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "business_status": place.get("businessStatus"),
        },
        "facilities": {
            "wheelchair_accessible_entrance": accessibility.get(
                "wheelchairAccessibleEntrance"
            ),
            "wheelchair_accessible_parking": accessibility.get(
                "wheelchairAccessibleParking"
            ),
            "restroom": place.get("restroom"),
            "free_parking_lot": parking.get("freeParkingLot"),
            "paid_parking_lot": parking.get("paidParkingLot"),
            "accepts_nfc": payment.get("acceptsNfc"),
        },
        "raw": place,
    }
