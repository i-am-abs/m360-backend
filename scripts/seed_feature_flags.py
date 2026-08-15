from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pymongo import MongoClient

COLLECTION = "feature_flag_locations"

_LAUNCHED_FEATURES = {
    "verification": True,
    "timings": True,
    "committee_registration": True,
    "masjid_discovery": True,
}

LOCATIONS = [
    {
        "location_key": "*",
        "country": None,
        "state": None,
        "city": None,
        "aliases": None,
        "bounds": None,
        "center": None,
        "radius_km": None,
        "features": {
            "verification": True,
            "timings": True,
            "committee_registration": True,
            "masjid_discovery": False,
        },
        "priority": 0,
        "enabled": True,
    },
    {
        "location_key": "IN-DL",
        "country": "IN",
        "state": "DL",
        "city": None,
        "aliases": {
            "country": ["IN", "India"],
            "state": ["DL", "Delhi", "NCT of Delhi"],
        },
        "bounds": None,
        "center": None,
        "radius_km": None,
        "features": dict(_LAUNCHED_FEATURES),
        "priority": 10,
        "enabled": True,
    },
    {
        "location_key": "IN-DL-Delhi",
        "country": "IN",
        "state": "DL",
        "city": "Delhi",
        "aliases": {
            "country": ["IN", "India"],
            "state": ["DL", "Delhi", "NCT of Delhi"],
            "city": ["Delhi", "New Delhi"],
        },
        "bounds": None,
        "center": {"latitude": 28.6139, "longitude": 77.2090},
        "radius_km": 30,
        "features": dict(_LAUNCHED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    {
        "location_key": "IN-UP-Aligarh",
        "country": "IN",
        "state": "UP",
        "city": "Aligarh",
        "aliases": {
            "country": ["IN", "India"],
            "state": ["UP", "Uttar Pradesh", "UttarPradesh", "Utter Pradesh"],
            "city": ["Aligarh", "Aligarh District", "Koil", "Aligarh City"],
        },
        "bounds": {
            "lat_min": 27.70,
            "lat_max": 28.15,
            "lng_min": 77.80,
            "lng_max": 78.35,
        },
        "center": {"latitude": 27.8974, "longitude": 78.0880},
        "radius_km": 32,
        "features": dict(_LAUNCHED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    {
        "location_key": "IN-UttarPradesh-Aligarh",
        "country": "IN",
        "state": "Uttar Pradesh",
        "city": "Aligarh",
        "aliases": {
            "country": ["IN", "India"],
            "state": ["UP", "Uttar Pradesh", "UttarPradesh"],
            "city": ["Aligarh", "Aligarh District", "Koil"],
        },
        "bounds": {
            "lat_min": 27.70,
            "lat_max": 28.15,
            "lng_min": 77.80,
            "lng_max": 78.35,
        },
        "center": {"latitude": 27.8974, "longitude": 78.0880},
        "radius_km": 32,
        "features": dict(_LAUNCHED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    {
        "location_key": "IN-HR-Faridabad",
        "country": "IN",
        "state": "HR",
        "city": "Faridabad",
        "aliases": {
            "country": ["IN", "India"],
            "state": ["HR", "Haryana"],
            "city": ["Faridabad", "Ballabgarh"],
        },
        "bounds": None,
        "center": {"latitude": 28.4089, "longitude": 77.3178},
        "radius_km": 16,
        "features": dict(_LAUNCHED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
]

# Superseded by the alias lists above; leaving them would reintroduce ambiguous
# duplicate regions for the same city.
OBSOLETE_LOCATION_KEYS = [
    "IN-Delhi-Delhi",
    "IN-Haryana-Faridabad",
]


def main() -> None:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        print("Set MONGODB_URI", file=sys.stderr)
        sys.exit(1)

    db_name = os.environ.get("MONGODB_DATABASE", "m360")
    now = datetime.now(timezone.utc).isoformat()
    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    col = client[db_name][COLLECTION]

    for doc in LOCATIONS:
        key = doc["location_key"]
        col.update_one(
            {"location_key": key},
            {
                "$set": {**doc, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        print(f"upserted location_key={key}")

    removed = col.delete_many({"location_key": {"$in": OBSOLETE_LOCATION_KEYS}})
    if removed.deleted_count:
        print(f"removed {removed.deleted_count} obsolete duplicate location(s)")

    client.close()
    print("done")


if __name__ == "__main__":
    main()
