"""
app/core/security.py
Token sesi anonim, tautan unduhan bertanda waktu.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Optional

from app.core.config import settings


def generate_session_token() -> str:
    """Buat token sesi anonim yang acak (32 byte hex)."""
    return os.urandom(32).hex()


def generate_job_id() -> str:
    """Buat ID job unik yang pendek."""
    return os.urandom(16).hex()


def sign_download_url(job_id: str, filename: str, ttl_seconds: int = 1800) -> str:
    """
    Buat query-string bertanda waktu untuk URL unduhan sementara.
    Format: expires=<unix>&sig=<hmac>
    """
    expires = int(time.time()) + ttl_seconds
    payload = f"{job_id}:{filename}:{expires}"
    sig = hmac.new(
        settings.secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"expires={expires}&sig={sig}"


def verify_download_token(job_id: str, filename: str, expires: int, sig: str) -> bool:
    """Verifikasi token unduhan."""
    if time.time() > expires:
        return False
    payload = f"{job_id}:{filename}:{expires}"
    expected = hmac.new(
        settings.secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig)
