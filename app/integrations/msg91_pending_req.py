from __future__ import annotations

import threading
import time
from typing import Optional, Tuple


class Msg91PendingReqIdStore:
    """Buffers requestId from MSG91 webhooks when sendOtp HTTP body does not include it yet."""

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._entries: dict[str, Tuple[str, float]] = {}

    def discard_identifier(self, identifier: str) -> None:
        ident = str(identifier).strip()
        with self._lock:
            self._entries.pop(ident, None)

    def record(self, identifier: str, request_id: str) -> None:
        if not identifier or not request_id:
            return
        ident = str(identifier).strip()
        rid = str(request_id).strip()
        with self._lock:
            self._entries[ident] = (rid, time.monotonic() + self._ttl)

    def take(self, identifier: str) -> Optional[str]:
        ident = str(identifier).strip()
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


msg91_pending_req_id_store = Msg91PendingReqIdStore()
