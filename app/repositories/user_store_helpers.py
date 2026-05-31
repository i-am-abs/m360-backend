from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.utils.phone import canonicalize_india_phone, phone_lookup_variants


def resolve_canonical_phone(phone_number: str, country_code: str = "91") -> str:
    return canonicalize_india_phone(phone_number, country_code)


def find_matching_users(users_by_key: Dict[str, Dict[str, Any]], phone_number: str, country_code: str = "91",) -> List[Tuple[str, Dict[str, Any]]]:
    variants = set(phone_lookup_variants(phone_number, country_code))
    matches: List[Tuple[str, Dict[str, Any]]] = []
    seen_user_ids: set[str] = set()
    for key, user in users_by_key.items():
        stored_phone = str(user.get("phone_number") or key)
        if key in variants or stored_phone in variants:
            user_id = str(user.get("user_id") or "")
            if user_id and user_id in seen_user_ids:
                continue
            if user_id:
                seen_user_ids.add(user_id)
            matches.append((key, user))
    return matches


def pick_primary_user(matches: List[Tuple[str, Dict[str, Any]]]) -> Tuple[str, Dict[str, Any], List[Tuple[str, Dict[str, Any]]]]:
    ordered = sorted(
        matches,
        key=lambda item: str(item[1].get("created_at") or ""),
    )
    primary_key, primary_user = ordered[0]
    return primary_key, primary_user, ordered[1:]


def merge_favorite_place_ids(*favorite_lists: List[str]) -> List[str]:
    merged: List[str] = []
    seen: set[str] = set()
    for favorites in favorite_lists:
        for place_id in favorites:
            if place_id not in seen:
                seen.add(place_id)
                merged.append(place_id)
    return merged
