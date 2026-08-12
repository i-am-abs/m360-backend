from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from app.interfaces.feature_flag_repository import FeatureFlagRepository
from app.utils.region_match import best_coordinate_match, best_region_match


class CachedFeatureFlagStore(FeatureFlagRepository):
    """Keeps the (small) region catalog in process memory and matches locally.

    Caching the catalog rather than per-request answers matters because clients send
    raw GPS fixes: keying a cache on exact coordinates yields a near-zero hit rate and
    unbounded key growth, while the catalog is a handful of documents that every
    request can reuse.
    """

    def __init__(
            self,
            delegate: FeatureFlagRepository,
            ttl_seconds: int = 300,
            time_source: Optional[Callable[[], float]] = None,
    ) -> None:
        self._delegate = delegate
        self._ttl = max(0, int(ttl_seconds))
        self._now = time_source or time.monotonic
        self._lock = threading.Lock()
        self._catalog: Optional[List[Dict[str, Any]]] = None
        self._expires_at = 0.0

    def invalidate(self) -> None:
        with self._lock:
            self._catalog = None
            self._expires_at = 0.0

    def _load(self) -> List[Dict[str, Any]]:
        if self._ttl <= 0:
            return self._delegate.list_all()

        now = self._now()
        with self._lock:
            if self._catalog is not None and now < self._expires_at:
                return self._catalog

        # Refresh outside the lock so a slow Mongo call cannot block readers.
        fresh = self._delegate.list_all()
        with self._lock:
            self._catalog = fresh
            self._expires_at = self._now() + self._ttl
        return fresh

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._load())

    def find_by_location_key(self, location_key: str) -> Optional[Dict[str, Any]]:
        if not location_key:
            return None
        for doc in self._load():
            if doc.get("location_key") == location_key:
                return doc
        return None

    def find_by_coordinates(
            self,
            latitude: float,
            longitude: float,
    ) -> Optional[Dict[str, Any]]:
        return best_coordinate_match(self._load(), latitude, longitude)

    def find_by_region(
            self,
            country: Optional[str],
            state: Optional[str],
            city: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        return best_region_match(self._load(), country, state, city)
