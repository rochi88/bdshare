"""
bdshare.util.cache
~~~~~~~~~~~~~~~~~~
Simple in-process TTL cache used by the BDShare OOP client,
plus a module-level ``clear_cache()`` for the functional API.
"""

import time
import threading
from typing import Any, Dict, Optional, Tuple


class _TTLCache:
    """
    Thread-safe in-process key/value cache with per-entry TTL.

    Values are evicted lazily on read once their TTL has expired.
    """

    def __init__(self):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock  = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for *key*, or ``None`` if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Store *value* under *key* with a TTL of *ttl* seconds.

        :param ttl: Time-to-live in seconds (default 300 = 5 minutes).
        """
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def clear(self) -> None:
        """Evict all cached entries."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# Module-level singleton used by BDShare client instances
_cache = _TTLCache()


def clear_cache() -> None:
    """
    Clear the module-level cache.

    Called by ``BDShare.clear_cache()`` and ``BDShare.__exit__``.
    """
    _cache.clear()