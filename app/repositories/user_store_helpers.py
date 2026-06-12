from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.enums.masjid import MasjidSaveLimit
from app.utils.phone import canonicalize_india_phone, phone_lookup_variants


def resolve_canonical_phone(phone_number: str, country_code: str = "91") -> str:
    return canonicalize_india_phone(phone_number, country_code)


def find_matching_users(
        users_by_key: Dict[str, Dict[str, Any]],
        phone_number: str,
        country_code: str = "91",
) -> List[Tuple[str, Dict[str, Any]]]:
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


def pick_primary_user(
        matches: List[Tuple[str, Dict[str, Any]]],
) -> Tuple[str, Dict[str, Any], List[Tuple[str, Dict[str, Any]]]]:
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


def prepare_favorites_by_phone(data: Dict[str, Any]) -> bool:
    changed = False
    favorites_by_phone = data.setdefault("favorites_by_phone", {})
    favorites_by_user_id = data.get("favorites_by_user_id") or {}

    user_id_to_phone: Dict[str, str] = {}
    for key, user in (data.get("users_by_phone") or {}).items():
        user_id = str(user.get("user_id") or "")
        if not user_id:
            continue
        try:
            user_id_to_phone[user_id] = resolve_canonical_phone(
                str(user.get("phone_number") or key),
            )
        except ValueError:
            user_id_to_phone[user_id] = str(user.get("phone_number") or key)

    for user_id, place_ids in favorites_by_user_id.items():
        phone = user_id_to_phone.get(user_id)
        if not phone:
            continue
        existing = favorites_by_phone.get(phone, [])
        favorites_by_phone[phone] = merge_favorite_place_ids(
            existing,
            list(place_ids or []),
        )
        changed = True

    if favorites_by_user_id:
        data["favorites_by_user_id"] = {}
        changed = True

    canonicalized: Dict[str, List[str]] = {}
    for phone_key, place_ids in list(favorites_by_phone.items()):
        try:
            canonical = resolve_canonical_phone(phone_key)
        except ValueError:
            canonical = phone_key
        canonicalized[canonical] = merge_favorite_place_ids(
            canonicalized.get(canonical, []),
            list(place_ids or []),
        )
        if canonical != phone_key:
            changed = True

    if canonicalized != favorites_by_phone:
        data["favorites_by_phone"] = canonicalized
        changed = True

    max_favorites = MasjidSaveLimit.MAX_FAVORITES.value
    for phone, place_ids in list(data["favorites_by_phone"].items()):
        if len(place_ids) > max_favorites:
            data["favorites_by_phone"][phone] = place_ids[:max_favorites]
            changed = True

    return changed


def list_favorites_for_phone(data: Dict[str, Any], phone_number: str) -> List[str]:
    prepare_favorites_by_phone(data)
    phone = resolve_canonical_phone(phone_number)
    return list(data.get("favorites_by_phone", {}).get(phone, []))


def set_favorites_for_phone(
        data: Dict[str, Any],
        phone_number: str,
        place_ids: List[str],
) -> None:
    prepare_favorites_by_phone(data)
    phone = resolve_canonical_phone(phone_number)
    data.setdefault("favorites_by_phone", {})[phone] = list(place_ids)
