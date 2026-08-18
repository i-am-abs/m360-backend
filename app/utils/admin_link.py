from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.enums.committee_designation import CommitteeDesignation
from app.core.enums.role import UserRole
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.utils.masjid import normalize_place_id
from app.utils.phone import phone_lookup_variants


def committee_member_from_admin(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc.get("designation"):
        designation = CommitteeDesignation.normalize(doc.get("designation"))
    elif doc.get("role") not in UserRole.values():
        designation = CommitteeDesignation.normalize(doc.get("role"))
    else:
        designation = CommitteeDesignation.ADMIN.value

    return {
        "adminId": doc.get("admin_id"),
        "name": doc.get("name"),
        "phone": doc.get("phone"),
        "role": designation,
        "designation": designation,
        "designationLabel": CommitteeDesignation.labels().get(
            designation,
            designation.replace("_", " ").title(),
        ),
        "status": doc.get("status"),
        "committeeId": doc.get("committee_id"),
        "profileImage": doc.get("profile_image"),
        "masjidPlaceId": doc.get("masjid_place_id"),
    }


def _normalize_stored_member(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    if not any(item.get(k) for k in ("name", "phone", "admin_id", "adminId")):
        return None
    designation = CommitteeDesignation.normalize(
        item.get("designation") or item.get("role"),
    )
    return {
        "adminId": item.get("adminId") or item.get("admin_id"),
        "name": item.get("name"),
        "phone": item.get("phone"),
        "role": designation,
        "designation": designation,
        "designationLabel": CommitteeDesignation.labels().get(
            designation,
            designation.replace("_", " ").title(),
        ),
        "status": item.get("status"),
        "committeeId": item.get("committeeId") or item.get("committee_id"),
        "profileImage": item.get("profileImage") or item.get("profile_image"),
        "masjidPlaceId": item.get("masjidPlaceId") or item.get("masjid_place_id"),
    }


def resolve_committee_for_place(
        place_id: str,
        *,
        admin_store: Optional[AdminRepository] = None,
        masjid_store: Optional[MasjidRepository] = None,
) -> Dict[str, Any]:
    """Build committee payload; details is always a list of members."""
    if admin_store is not None:
        admins = admin_store.list_approved_for_place(place_id)
        if admins:
            details = [committee_member_from_admin(doc) for doc in admins]
            return {
                "hasCommittee": True,
                "has_committee": True,
                "details": details,
            }

    if masjid_store is not None:
        stored = masjid_store.get_committee(place_id)
        if stored:
            nested = stored.get("committee")
            members: List[Dict[str, Any]] = []
            if isinstance(nested, list):
                for item in nested:
                    normalized = _normalize_stored_member(item)
                    if normalized:
                        members.append(normalized)
            elif isinstance(nested, dict):
                normalized = _normalize_stored_member(nested)
                if normalized:
                    members.append(normalized)
            elif any(stored.get(k) for k in ("name", "phone", "admin_id", "adminId")):
                normalized = _normalize_stored_member(stored)
                if normalized:
                    members.append(normalized)
            if members:
                return {
                    "hasCommittee": True,
                    "has_committee": True,
                    "details": members,
                }

    return {"hasCommittee": False, "has_committee": False, "details": []}


def _approved_admin_docs(
        *,
        current_user: Optional[Dict[str, Any]],
        admin_store: Optional[AdminRepository],
) -> List[Dict[str, Any]]:
    if not current_user or admin_store is None:
        return []

    seen: set[str] = set()
    docs: List[Dict[str, Any]] = []
    user_id = str(current_user.get("user_id") or "")
    phone = current_user.get("phone_number")

    candidates: List[Dict[str, Any]] = []
    if user_id:
        candidates.extend(ensure_admin_user_link(
            admin_store,
            user_id=user_id,
            phone=str(phone) if phone else None,
        ))
    if phone:
        candidates.extend(admin_store.list_by_phone(str(phone), status="approved"))

    for doc in candidates:
        if doc.get("status") != "approved":
            continue
        admin_id = str(doc.get("admin_id") or "")
        key = admin_id or f"{doc.get('phone')}:{doc.get('masjid_place_id')}"
        if key in seen:
            continue
        seen.add(key)
        docs.append(doc)
    return docs


def is_user_admin_for_place(
        place_id: str,
        *,
        current_user: Optional[Dict[str, Any]],
        admin_store: Optional[AdminRepository],
) -> bool:
    target = normalize_place_id(place_id)
    if not target:
        return False
    for doc in _approved_admin_docs(current_user=current_user, admin_store=admin_store):
        if normalize_place_id(str(doc.get("masjid_place_id") or "")) == target:
            return True
    return False


def ensure_admin_user_link(
        admin_store: AdminRepository,
        *,
        user_id: str,
        phone: Optional[str],
) -> List[Dict[str, Any]]:
    """Link admin rows for this phone to user_id; return docs for the user."""
    if not user_id:
        return []

    linked = admin_store.list_by_user_id(user_id)
    if linked:
        return linked

    if not phone:
        return []

    matches = admin_store.list_by_phone(phone)
    for doc in matches:
        admin_id = doc.get("admin_id")
        if not admin_id:
            continue
        updates: Dict[str, Any] = {}
        if doc.get("user_id") != user_id:
            updates["user_id"] = user_id
        try:
            from app.utils.phone import canonicalize_india_phone
            canonical = canonicalize_india_phone(phone)
            if doc.get("phone") != canonical:
                updates["phone"] = canonical
        except ValueError:
            pass
        if updates:
            if "user_id" in updates and len(updates) == 1:
                admin_store.link_user(str(admin_id), user_id)
            else:
                admin_store.update_fields(str(admin_id), updates)
    return admin_store.list_by_user_id(user_id)


def phones_match(left: str, right: str) -> bool:
    left_variants = set(phone_lookup_variants(left))
    right_variants = set(phone_lookup_variants(right))
    return bool(left_variants & right_variants)


def resolve_system_role_and_designation(role_value: str) -> tuple[str, str]:
    """Map request role/designation → (system_role, designation)."""
    raw = (role_value or "").strip().lower().replace(" ", "_")
    if raw == UserRole.SUPER_ADMIN.value:
        return UserRole.SUPER_ADMIN.value, CommitteeDesignation.ADMIN.value
    if raw in CommitteeDesignation.values() or raw in {
        "muazzin", "moazzin", "masjid_admin", "committee", "member",
    }:
        designation = CommitteeDesignation.normalize(raw)
        return UserRole.ADMIN.value, designation
    if raw == UserRole.ADMIN.value:
        return UserRole.ADMIN.value, CommitteeDesignation.ADMIN.value
    raise ValueError(
        f"role must be one of: {', '.join(sorted(set(CommitteeDesignation.values()) | {UserRole.SUPER_ADMIN.value}))}"
    )
