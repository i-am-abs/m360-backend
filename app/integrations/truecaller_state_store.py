from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, Dict

from app.core.logging import get_logger

_log = get_logger(__name__)


class TruecallerStateStore:
    """Single-use registry of Truecaller ``oauth_state`` values.

    The app generates the state and the Truecaller SDK checks it on-device, so the
    backend has nothing to compare it against; it instead rejects any state seen
    before, which blocks replays and concurrent duplicates of one login attempt.
    Only a hash of the state is stored.
    """

    def __init__(
            self,
            *,
            redis_client: Any = None,
            ttl_seconds: int = 900,
            key_prefix: str = "m360",
    ) -> None:
        self._redis = redis_client
        self._ttl = max(1, int(ttl_seconds))
        self._pfx = (key_prefix or "m360").strip() or "m360"
        self._lock = threading.Lock()
        self._entries: Dict[str, float] = {}

    def claim(self, state: str) -> bool:
        key = f"{self._pfx}:truecaller:state:{hashlib.sha256(state.encode()).hexdigest()}"
        if self._redis is not None:
            try:
                return bool(self._redis.set(key, "1", nx=True, ex=self._ttl))
            except Exception as exc:
                _log.warning("Truecaller state store unavailable, using memory: %s", exc)
        now = time.monotonic()
        with self._lock:
            self._entries = {k: v for k, v in self._entries.items() if v > now}
            if key in self._entries:
                return False
            self._entries[key] = now + self._ttl
            return True
