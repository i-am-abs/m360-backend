#!/usr/bin/env python3
"""Link existing admins to users by phone and optionally assign a masjid place_id."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from pymongo import MongoClient

from app.utils.phone import canonicalize_india_phone, phone_lookup_variants


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", required=True, help="10-digit or 91... phone")
    parser.add_argument("--place-id", default=None, help="Optional masjid place id to assign")
    parser.add_argument("--approve", action="store_true", help="Force status=approved")
    args = parser.parse_args()

    uri = os.environ.get("MONGODB_URI")
    if not uri:
        print("Set MONGODB_URI", file=sys.stderr)
        return 1

    db = MongoClient(uri, serverSelectionTimeoutMS=10_000)[
        os.environ.get("MONGODB_DATABASE", "muslim360")
    ]
    phone = canonicalize_india_phone(args.phone)
    variants = phone_lookup_variants(phone)

    user = db["users"].find_one({"phone_number": {"$in": variants}})
    if not user:
        print(f"No user for phone variants {variants}. Login via OTP first.")
        return 1

    user_id = user["user_id"]
    admins = list(db["admins"].find({"phone": {"$in": variants}}))
    if not admins:
        print(f"No admin row for {phone}. Register first.")
        return 1

    for admin in admins:
        update = {
            "user_id": user_id,
            "phone": phone,
        }
        if args.place_id:
            update["masjid_place_id"] = args.place_id
        if args.approve:
            update["status"] = "approved"
        db["admins"].update_one({"admin_id": admin["admin_id"]}, {"$set": update})
        print(
            f"Updated admin_id={admin['admin_id']} user_id={user_id} "
            f"phone={phone} place={update.get('masjid_place_id', admin.get('masjid_place_id'))} "
            f"status={update.get('status', admin.get('status'))}"
        )

        if args.place_id and update.get("status", admin.get("status")) == "approved":
            db["masjid_committees"].update_one(
                {"place_id": args.place_id},
                {
                    "$set": {
                        "committee": {
                            "adminId": admin["admin_id"],
                            "name": admin.get("name"),
                            "phone": phone,
                            "role": admin.get("role"),
                            "status": "approved",
                            "committeeId": admin.get("committee_id"),
                            "profileImage": admin.get("profile_image"),
                        }
                    },
                    "$setOnInsert": {"timings": [], "amenities": []},
                },
                upsert=True,
            )
            print(f"Upserted masjid_committees for {args.place_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
