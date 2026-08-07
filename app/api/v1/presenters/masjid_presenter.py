from __future__ import annotations

from typing import Any, Dict, List, Optional


class MasjidDetailsPresenter:
    @staticmethod
    def to_view(
            place: Dict[str, Any],
            has_donations: bool = False,
            has_announcements: bool = True,
            donation_count: int = 0,
            announcement_count: int = 0,
            is_added: bool = False,
            saved_count: int = 0,
            committee_data: Optional[List[Dict[str, Any]]] = None,
            prayer_timings: Optional[List[Dict[str, Any]]] = None,
            amenities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        accessibility = place.get("accessibilityOptions") or {}
        parking = place.get("parkingOptions") or {}
        payment = place.get("paymentOptions") or {}
        prayers = list(prayer_timings or [])
        members = list(committee_data or [])
        return {
            "place_id": place.get("id"),
            "name": (place.get("displayName") or {}).get("text"),
            "address": place.get("formattedAddress"),
            "location": place.get("location"),
            "timings": prayers,
            "prayerTimings": prayers,
            "openingHours": {
                "current": place.get("currentOpeningHours"),
                "regular": place.get("regularOpeningHours"),
            },
            "amenities": list(amenities or []),
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
            "hasAnnouncementsEnabled": True,  # always on
            "donationUpdatesCount": donation_count,
            "announcementUpdatesCount": announcement_count,
            "isAddedToMyMasjid": is_added,
            "savedMasjidCount": saved_count,
            "committee_details": members,
            "committee": {
                "hasCommittee": len(members) > 0,
                "has_committee": len(members) > 0,
                "details": members,
            },
            "raw": place,
        }
