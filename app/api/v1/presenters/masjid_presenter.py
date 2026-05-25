from __future__ import annotations

from typing import Any, Dict

class MasjidDetailsPresenter:
    @staticmethod
    def toView(
            place: Dict[str, Any],
            hasDonations: bool = False,
            hasAnnouncements: bool = False,
            donationCount: int = 0,
            announcementCount: int = 0,
            isAdded: bool = False,
            savedCount: int = 0,
    ) -> Dict[str, Any]:
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
            "hasDonationsEnabled": hasDonations,
            "hasAnnouncementsEnabled": hasAnnouncements,
            "donationUpdatesCount": donationCount,
            "announcementUpdatesCount": announcementCount,
            "isAddedToMyMasjid": isAdded,
            "savedMasjidCount": savedCount,
            "raw": place,
        }
