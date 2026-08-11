from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pymongo import MongoClient

_ENABLED_FEATURES = {
    "verification": True,
    "timings": True,
    "committee_registration": True,
}

LOCATIONS = [
    {
        "location_key": "*",
        "country": None,
        "state": None,
        "city": None,
        "bounds": None,
        "features": {
            "verification": True,
            "timings": True,
            "committee_registration": True,
        },
        "priority": 0,
        "enabled": True,
    },
    # --- Delhi (state-level + city variants) ---
    {
        "location_key": "IN-DL",
        "country": "IN",
        "state": "DL",
        "city": None,
        "bounds": {
            "lat_min": 28.4,
            "lat_max": 28.9,
            "lng_min": 76.8,
            "lng_max": 77.4,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 10,
        "enabled": True,
    },
    {
        "location_key": "IN-DL-Delhi",
        "country": "IN",
        "state": "DL",
        "city": "Delhi",
        "bounds": {
            "lat_min": 28.4,
            "lat_max": 28.9,
            "lng_min": 76.8,
            "lng_max": 77.4,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    {
        "location_key": "IN-Delhi-Delhi",
        "country": "IN",
        "state": "Delhi",
        "city": "Delhi",
        "bounds": {
            "lat_min": 28.4,
            "lat_max": 28.9,
            "lng_min": 76.8,
            "lng_max": 77.4,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    # --- Aligarh, Uttar Pradesh ---
    {
        "location_key": "IN-UP-Aligarh",
        "country": "IN",
        "state": "UP",
        "city": "Aligarh",
        "bounds": {
            "lat_min": 27.80,
            "lat_max": 28.00,
            "lng_min": 77.95,
            "lng_max": 78.20,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    {
        "location_key": "IN-UttarPradesh-Aligarh",
        "country": "IN",
        "state": "Uttar Pradesh",
        "city": "Aligarh",
        "bounds": {
            "lat_min": 27.80,
            "lat_max": 28.00,
            "lng_min": 77.95,
            "lng_max": 78.20,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    # --- Faridabad, Haryana ---
    {
        "location_key": "IN-HR-Faridabad",
        "country": "IN",
        "state": "HR",
        "city": "Faridabad",
        "bounds": {
            "lat_min": 28.30,
            "lat_max": 28.50,
            "lng_min": 77.20,
            "lng_max": 77.40,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
    {
        "location_key": "IN-Haryana-Faridabad",
        "country": "IN",
        "state": "Haryana",
        "city": "Faridabad",
        "bounds": {
            "lat_min": 28.30,
            "lat_max": 28.50,
            "lng_min": 77.20,
            "lng_max": 77.40,
        },
        "features": dict(_ENABLED_FEATURES),
        "priority": 20,
        "enabled": True,
    },
]


def main() -> None:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        print("Set MONGODB_URI", file=sys.stderr)
        sys.exit(1)

    db_name = os.environ.get("MONGODB_DATABASE", "m360")
    now = datetime.now(timezone.utc).isoformat()
    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    col = client[db_name]["feature_flag_locations"]

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

    client.close()
    print("done")


if __name__ == "__main__":
    main()
