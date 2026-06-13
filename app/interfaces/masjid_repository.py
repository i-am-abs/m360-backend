from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MasjidRepository(ABC):
    """Abstract interface for persisting and retrieving masjid-specific data.

    This is intentionally separate from ``MasjidSearchService`` (which wraps
    the Google Places API) so that internally-managed data (committee info,
    prayer timings, amenities) lives in our own database and can evolve
    independently of the external Places data.
    """

    @abstractmethod
    def get_committee(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Return the committee document for the given *place_id*, or ``None``
        if no committee has been registered for this masjid.

        The returned dict (when present) has the shape::

            {
                "committee": {
                    "name": str,
                    "contact_phone": str | None,
                    "contact_email": str | None,
                    "established_year": int | None,
                },
                "timings": [
                    {
                        "prayer": "fajr" | "dhuhr" | "asr" | "maghrib" | "isha",
                        "adhan":  "HH:MM",
                        "iqamah": "HH:MM",
                    },
                    ...
                ],
                "amenities": ["car_parking", "ac", ...],
                "created_at": str,   # ISO-8601
                "updated_at": str,   # ISO-8601
            }
        """

    @abstractmethod
    def upsert_committee(
        self,
        place_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create or fully replace the committee document for *place_id*.

        Returns the stored document (with ``created_at`` / ``updated_at``
        populated).
        """
