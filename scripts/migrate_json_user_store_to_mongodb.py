#!/usr/bin/env python3

from __future__ import annotations

from typing import Optional

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings


def parseIsoTimestamp(rawTimestamp: Optional[str]) -> Optional[datetime]:
    if not rawTimestamp:
        return None
    parsedTimestamp = datetime.fromisoformat(rawTimestamp)
    if parsedTimestamp.tzinfo is None:
        return parsedTimestamp.replace(tzinfo=timezone.utc)
    return parsedTimestamp


def migrateUsers(usersByPhone: dict, usersCollection) -> int:
    migratedCount = 0
    for phoneNumber, userPayload in usersByPhone.items():
        usersCollection.update_one(
            {"phone_number": phoneNumber},
            {"$setOnInsert": userPayload},
            upsert=True,
        )
        migratedCount += 1
    return migratedCount


def migrateSessions(sessionsByToken: dict, sessionsCollection) -> int:
    migratedCount = 0
    for accessToken, sessionPayload in sessionsByToken.items():
        sessionDocument = {
            "access_token": accessToken,
            "user_id": sessionPayload["user_id"],
        }
        expiresAt = parseIsoTimestamp(sessionPayload.get("expires_at"))
        if expiresAt is not None:
            sessionDocument["expires_at"] = expiresAt
        sessionsCollection.update_one(
            {"access_token": accessToken},
            {"$set": sessionDocument},
            upsert=True,
        )
        migratedCount += 1
    return migratedCount


def migrateFavorites(favoritesByUserId: dict, favoritesCollection) -> int:
    migratedCount = 0
    for userId, placeIds in favoritesByUserId.items():
        favoritesCollection.update_one(
            {"user_id": userId},
            {
                "$set": {"user_id": userId},
                "$addToSet": {"place_ids": {"$each": list(placeIds or [])}},
            },
            upsert=True,
        )
        migratedCount += 1
    return migratedCount


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate JSON user store to MongoDB Atlas.")
    parser.add_argument(
        "--json-file",
        default="data/user_store.json",
        help="Path to the JSON user store file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print migration summary without writing to MongoDB.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.mongodb_configured:
        print("MongoDB is not configured. Set MONGODB_ENABLED=true and MONGODB_URI.")
        return 1

    jsonFilePath = Path(args.json_file)
    if not jsonFilePath.is_file():
        print(f"JSON file not found: {jsonFilePath}")
        return 1

    with jsonFilePath.open("r", encoding="utf-8") as jsonFile:
        jsonPayload = json.load(jsonFile)

    usersByPhone = jsonPayload.get("users_by_phone") or {}
    sessionsByToken = jsonPayload.get("sessions") or {}
    favoritesByUserId = jsonPayload.get("favorites_by_user_id") or {}

    print(f"Found {len(usersByPhone)} users, {len(sessionsByToken)} sessions, {len(favoritesByUserId)} favorite lists.")

    if args.dry_run:
        print("Dry run complete. No data written.")
        return 0

    mongoClient = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=10_000)
    mongoClient.admin.command("ping")
    database = mongoClient.get_database(settings.mongodb_database)

    usersCollection = database["users"]
    sessionsCollection = database["sessions"]
    favoritesCollection = database["favorites"]

    usersCollection.create_index("phone_number", unique=True)
    usersCollection.create_index("user_id", unique=True)
    sessionsCollection.create_index("access_token", unique=True)
    sessionsCollection.create_index("expires_at", expireAfterSeconds=0)
    favoritesCollection.create_index("user_id", unique=True)

    migratedUsers = migrateUsers(usersByPhone, usersCollection)
    migratedSessions = migrateSessions(sessionsByToken, sessionsCollection)
    migratedFavorites = migrateFavorites(favoritesByUserId, favoritesCollection)

    print(
        f"Migration complete into database '{settings.mongodb_database}': "
        f"users={migratedUsers}, sessions={migratedSessions}, favorites={migratedFavorites}"
    )
    mongoClient.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
