from __future__ import annotations

from typing import Any, Dict


class MasjidDetailsPresenter:
    @staticmethod
    def to_view(place: Dict[str, Any], has_donations: bool = False, has_announcements: bool = False, donation_count: int = 0, announcement_count: int = 0, is_added: bool = False, saved_count: int = 0,) -> Dict[str, Any]:
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
                "wheelchair_accessible_entrance": accessibility.get("wheelchairAccessibleEntrance"),
                "wheelchair_accessible_parking": accessibility.get("wheelchairAccessibleParking"),
                "restroom": place.get("restroom"),
                "free_parking_lot": parking.get("freeParkingLot"),
                "paid_parking_lot": parking.get("paidParkingLot"),
                "accepts_nfc": payment.get("acceptsNfc"),
            },
            "hasDonationsEnabled": has_donations,
            "hasAnnouncementsEnabled": has_announcements,
            "donationUpdatesCount": donation_count,
            "announcementUpdatesCount": announcement_count,
            "isAddedToMyMasjid": is_added,
            "savedMasjidCount": saved_count,
            "raw": place,
        }
