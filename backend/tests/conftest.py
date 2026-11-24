"""
tests/conftest.py
Konfigurasi pytest – patch database untuk pengujian tanpa MySQL.
"""

from __future__ import annotations

import pytest


def pytest_configure(config):
    """Aktifkan asyncio mode untuk pytest-asyncio."""
    pass


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """
    Patch engine database sehingga tes berjalan tanpa MySQL.
    Model tetap dapat diimport.
    """
    # Jika diperlukan koneksi DB dalam test, mock di sini
    pass
