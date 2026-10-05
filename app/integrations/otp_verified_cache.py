from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, Dict

from app.core.logging import get_logger

_log = get_logger(__name__)


class VerifiedOtpCache:
    """Short-lived record of (phone, reqId, otp) triples MSG91 already accepted.

    MSG91 consumes an OTP on the first successful verify, so a duplicate submit
    of the same correct OTP would otherwise fail. Only a hash is stored and the
    exact OTP is required, so this never lets an unverified code through.
    """

    def __init__(
            self,
            *,
            redis_client: Any = None,
            ttl_seconds: int = 120,
            key_prefix: str = "m360",
    ) -> None:
        self._redis = redis_client
        self._ttl = max(1, int(ttl_seconds))
        self._pfx = (key_prefix or "m360").strip() or "m360"
        self._lock = threading.Lock()
        self._entries: Dict[str, float] = {}

    def _key(self, phone: str, req_id: str, otp: str) -> str:
        digest = hashlib.sha256(f"{phone}|{req_id}|{otp}".encode()).hexdigest()
        return f"{self._pfx}:otp:verified:{digest}"

    def was_verified(self, phone: str, req_id: str, otp: str) -> bool:
        key = self._key(phone, req_id, otp)
        if self._redis is not None:
            try:
                return bool(self._redis.exists(key))
            except Exception as exc:
                _log.warning("Verified OTP cache read failed: %s", exc)
                return False
        now = time.monotonic()
        with self._lock:
            exp = self._entries.get(key)
            if exp is None:
                return False
            if exp <= now:
                self._entries.pop(key, None)
                return False
            return True

    def mark_verified(self, phone: str, req_id: str, otp: str) -> None:
        key = self._key(phone, req_id, otp)
        if self._redis is not None:
            try:
                self._redis.setex(key, self._ttl, "1")
            except Exception as exc:
                _log.warning("Verified OTP cache write failed: %s", exc)
            return
        now = time.monotonic()
        with self._lock:
            self._entries = {k: v for k, v in self._entries.items() if v > now}
            self._entries[key] = now + self._ttl
