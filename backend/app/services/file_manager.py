"""
app/services/file_manager.py
Manajemen file sementara per sesi (PRD §11, §FR-20).
- Nama file acak, terikat token sesi
- Hapus otomatis setelah TTL
- Tombol "Hapus sekarang"
- Tidak ada penyimpanan permanen
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import logger


class FileManager:
    """
    Mengelola direktori sementara per job.
    Layout: TEMP_DIR/<job_id>/{input/, output/, reference/}
    """

    def __init__(self, base_dir: Optional[str] = None, ttl_minutes: Optional[int] = None):
        self._base = Path(base_dir or settings.temp_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = (ttl_minutes or settings.file_ttl_minutes) * 60
        self._expires: dict[str, float] = {}
        self._lock = threading.Lock()

    # ----- Direktori Job -----

    def create_job_dir(self, job_id: str) -> Path:
        job_dir = self._base / job_id
        (job_dir / "input").mkdir(parents=True, exist_ok=True)
        (job_dir / "output").mkdir(parents=True, exist_ok=True)
        (job_dir / "reference").mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._expires[job_id] = time.time() + self._ttl_seconds
        return job_dir

    def get_job_dir(self, job_id: str) -> Optional[Path]:
        path = self._base / job_id
        return path if path.exists() else None

    def input_path(self, job_id: str, filename: str) -> Path:
        return self._base / job_id / "input" / filename

    def output_path(self, job_id: str, filename: str) -> Path:
        return self._base / job_id / "output" / filename

    def reference_path(self, job_id: str, filename: str) -> Path:
        return self._base / job_id / "reference" / filename

    # ----- Penghapusan -----

    def delete_job(self, job_id: str) -> bool:
        """Hapus semua file job sekarang."""
        job_dir = self._base / job_id
        if job_dir.exists():
            try:
                shutil.rmtree(job_dir)
                with self._lock:
                    self._expires.pop(job_id, None)
                logger.info("job_deleted", job_id=job_id)
                return True
            except Exception as e:
                logger.error("delete_failed", job_id=job_id, error=str(e))
        return False

    def delete_reference(self, job_id: str) -> None:
        """Hapus folder referensi segera setelah ekstraksi (§FR-03)."""
        ref_dir = self._base / job_id / "reference"
        if ref_dir.exists():
            shutil.rmtree(ref_dir)
            logger.info("reference_deleted", job_id=job_id)

    def purge_expired(self) -> int:
        """Hapus semua job yang melewati TTL. Dipanggil oleh scheduler."""
        now = time.time()
        with self._lock:
            expired = [jid for jid, exp in self._expires.items() if now > exp]

        count = 0
        for job_id in expired:
            if self.delete_job(job_id):
                count += 1
        return count

    def extend_ttl(self, job_id: str, extra_seconds: int = 0) -> None:
        with self._lock:
            if job_id in self._expires:
                self._expires[job_id] = time.time() + self._ttl_seconds + extra_seconds

    def remaining_seconds(self, job_id: str) -> Optional[int]:
        with self._lock:
            exp = self._expires.get(job_id)
        if exp is None:
            return None
        return max(0, int(exp - time.time()))


# Singleton
file_manager = FileManager()
