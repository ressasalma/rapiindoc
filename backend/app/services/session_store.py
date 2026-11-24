"""
app/services/session_store.py
Penyimpanan status job sementara di memori (dict) dengan TTL.
Dapat diganti Redis di produksi.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class InMemorySessionStore:
    """
    Thread-safe in-memory store untuk status job.
    Key: job_id  |  Value: dict payload  |  TTL: detik
    """

    def __init__(self, default_ttl: int = 1800) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._expires: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    # ----- CRUD -----

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        ttl = ttl or self._default_ttl
        with self._lock:
            self._store[key] = value
            self._expires[key] = time.time() + ttl

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self._store:
                return None
            if time.time() > self._expires.get(key, 0):
                self._delete_locked(key)
                return None
            return self._store[key]

    def update(self, key: str, patch: Dict[str, Any]) -> bool:
        with self._lock:
            if key not in self._store:
                return False
            self._store[key].update(patch)
            return True

    def delete(self, key: str) -> None:
        with self._lock:
            self._delete_locked(key)

    def _delete_locked(self, key: str) -> None:
        self._store.pop(key, None)
        self._expires.pop(key, None)

    # ----- Pembersih terjadwal -----

    def purge_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, exp in self._expires.items() if now > exp]
            for k in expired:
                self._delete_locked(k)
        return len(expired)


# Singleton untuk aplikasi
session_store = InMemorySessionStore()
