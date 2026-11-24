"""
app/core/config.py
Konfigurasi aplikasi dari environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Aplikasi -----
    app_name: str = "RapiInDoc API"
    app_version: str = "1.0.0"
    app_env: str = "development"
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING"
    debug: bool = False
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ----- Database -----
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "rapiindoc"
    db_user: str = "root"
    db_password: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    # ----- Redis -----
    redis_url: str = "redis://localhost:6379/0"

    # ----- Storage sementara -----
    temp_dir: str = "/tmp/rapiindoc"
    file_ttl_minutes: int = 30
    max_file_size: int = 20 * 1024 * 1024  # 20 MB

    # ----- Rate Limiting -----
    rate_limit_upload: int = 10   # per IP per menit
    rate_limit_process: int = 5

    # ----- AI (opsional) -----
    ai_enabled: bool = False
    ai_provider: str = "openai"
    ai_api_key: Optional[str] = None
    ai_model: str = "gpt-4o-mini"
    ai_max_chunk_chars: int = 500

    # ----- LibreOffice -----
    libreoffice_path: str = "soffice"

    # ----- Jenis dokumen yang didukung -----
    supported_doc_types: List[str] = [
        "makalah",
        "laporan",
        "proposal",
        "jurnal",
        "lainnya",
    ]

    # Grup aturan (12 bagian per PRD §4)
    rule_groups: List[str] = [
        "halaman",
        "tipografi",
        "cover",
        "bagian_awal",
        "heading_bab",
        "penomoran_halaman",
        "daftar_isi",
        "tabel_gambar",
        "sitasi",
        "daftar_pustaka",
        "lampiran",
        "header_footer",
    ]

    @field_validator("temp_dir")
    @classmethod
    def _ensure_temp_dir(cls, v: str) -> str:
        import os
        os.makedirs(v, exist_ok=True)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
