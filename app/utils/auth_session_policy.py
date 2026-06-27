from __future__ import annotations

from app.core.enums.role import UserRole
from app.utils.session_ttl import session_never_expires

INFINITE_SESSION_TTL_SECONDS = 0

_SUPPORTED_ROLES = UserRole.values()


def resolve_session_ttl_seconds(
        configured_ttl_seconds: int,
        role: str | None = None,
        *,
        force_infinite: bool = True,
) -> int:
    if force_infinite:
        return INFINITE_SESSION_TTL_SECONDS
    if role and role not in _SUPPORTED_ROLES:
        return configured_ttl_seconds
    return configured_ttl_seconds


def auth_never_expires(ttl_seconds: int) -> bool:
    return session_never_expires(ttl_seconds)
