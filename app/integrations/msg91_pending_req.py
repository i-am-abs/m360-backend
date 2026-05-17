from __future__ import annotations

import threading
import time
from typing import Any, Optional, Tuple

from app.core.logging import get_logger

log = get_logger(__name__)


class Msg91PendingReqIdStore:
    def __init__(
            self,
            *,
            redis_client: Any = None,
            ttl_seconds: float = 300.0,
            key_prefix: str = "m360",
    ) -> None:
        self.redis_client = redis_client
        self.ttl_seconds = int(max(1, ttl_seconds))
        self.key_prefix = (key_prefix or "m360").strip() or "m360"
        self.lock = threading.Lock()
        self.entries: dict[str, Tuple[str, float]] = {}

    def pending_key(self, identifier: str) -> str:
        return f"{self.key_prefix}:msg91:pending:{identifier}"

    def discard_identifier(self, identifier: str) -> None:
        ident = str(identifier).strip()
        if self.redis_client is not None:
            try:
                self.redis_client.delete(self.pending_key(ident))
            except Exception as exc:
                log.warning("MSG91 pending redis delete failed: %s", exc)
            return
        with self.lock:
            self.entries.pop(ident, None)

    def record(self, identifier: str, request_id: str) -> None:
        if not identifier or not request_id:
            return
        ident = str(identifier).strip()
        rid = str(request_id).strip()
        if self.redis_client is not None:
            try:
                self.redis_client.setex(self.pending_key(ident), self.ttl_seconds, rid)
            except Exception as exc:
                log.warning("MSG91 pending redis set failed: %s", exc)
            return
        with self.lock:
            self.entries[ident] = (rid, time.monotonic() + float(self.ttl_seconds))

    def take(self, identifier: str) -> Optional[str]:
        ident = str(identifier).strip()
        if self.redis_client is not None:
            try:
                key = self.pending_key(ident)
                if hasattr(self.redis_client, "getdel"):
                    val = self.redis_client.getdel(key)
                else:
                    val = self.redis_client.get(key)
                    self.redis_client.delete(key)
                return str(val).strip() if val else None
            except Exception as exc:
                log.warning("MSG91 pending redis take failed: %s", exc)
                return None
        with self.lock:
            hit = self.entries.pop(ident, None)
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
