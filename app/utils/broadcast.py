from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

DEFAULT_EXPIRY_DAYS = 30
ALLOWED_EXPIRY_DAYS = {DEFAULT_EXPIRY_DAYS}


def compute_expires_at(
    expires_in_days: Optional[int],
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Return an ISO-8601 UTC expiry, or None when the post never expires."""
    if expires_in_days is None:
        return None
    days = expires_in_days if expires_in_days in ALLOWED_EXPIRY_DAYS else DEFAULT_EXPIRY_DAYS
    base = now or datetime.now(timezone.utc)
    return (base + timedelta(days=days)).isoformat()


def is_expired(expires_at: Optional[str], now: Optional[datetime] = None) -> bool:
    if not expires_at:
        return False
    try:
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= (now or datetime.now(timezone.utc))


def resolve_share_state(message: dict, now: Optional[datetime] = None) -> str:
    """Which share page to render. 'unavailable' takes precedence over 'expired'."""
    if message.get("allow_sharing", True) is False:
        return "unavailable"
    if is_expired(message.get("expires_at"), now):
        return "expired"
    return "available"
