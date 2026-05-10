from __future__ import annotations

import threading
import time
from typing import Any, Optional, Tuple

from app.core.logging import get_logger

_log = get_logger(__name__)


class Msg91PendingReqIdStore:
    """Buffers requestId from MSG91 webhooks when sendOtp HTTP body does not include it yet."""

    def __init__(
            self,
            *,
            redis_client: Any = None,
            ttl_seconds: float = 300.0,
            key_prefix: str = "m360",
    ) -> None:
        self._redis = redis_client
        self._ttl = int(max(1, ttl_seconds))
        self._pfx = (key_prefix or "m360").strip() or "m360"
        self._lock = threading.Lock()
        self._entries: dict[str, Tuple[str, float]] = {}

    def _pending_key(self, identifier: str) -> str:
        return f"{self._pfx}:msg91:pending:{identifier}"

    def discard_identifier(self, identifier: str) -> None:
        ident = str(identifier).strip()
        if self._redis is not None:
            try:
                self._redis.delete(self._pending_key(ident))
            except Exception as exc:
                _log.warning("MSG91 pending redis delete failed: %s", exc)
            return
        with self._lock:
            self._entries.pop(ident, None)

    def record(self, identifier: str, request_id: str) -> None:
        if not identifier or not request_id:
            return
        ident = str(identifier).strip()
        rid = str(request_id).strip()
        if self._redis is not None:
            try:
                self._redis.setex(self._pending_key(ident), self._ttl, rid)
            except Exception as exc:
                _log.warning("MSG91 pending redis set failed: %s", exc)
            return
        with self._lock:
            self._entries[ident] = (rid, time.monotonic() + float(self._ttl))

    def take(self, identifier: str) -> Optional[str]:
        ident = str(identifier).strip()
        if self._redis is not None:
            try:
                key = self._pending_key(ident)
                pipe = self._redis.pipeline()
                pipe.get(key)
                pipe.delete(key)
                val, _ = pipe.execute()
                return str(val).strip() if val else None
            except Exception as exc:
                _log.warning("MSG91 pending redis take failed: %s", exc)
                return None
        with self._lock:
            hit = self._entries.pop(ident, None)
        if hit is None:
            return None
        rid, exp = hit
        if time.monotonic() >= exp:
            return None
        return rid

    def wait_for(self, identifier: str, *, total_seconds: float, interval: float = 0.2) -> Optional[str]:
        deadline = time.monotonic() + total_seconds
        ident = str(identifier).strip()
        while time.monotonic() < deadline:
            rid = self.take(ident)
            if rid is not None:
                return rid
            time.sleep(interval)
        return None
