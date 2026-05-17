from __future__ import annotations

from typing import Optional


def session_never_expires(ttl_seconds: int) -> bool:
    return ttl_seconds <= 0


def session_expires_in(ttl_seconds: int) -> Optional[int]:
    if session_never_expires(ttl_seconds):
        return None
    return ttl_seconds
