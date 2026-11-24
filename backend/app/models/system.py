"""
app/models/system.py
Model SQLAlchemy – hanya data sistem sesuai PRD §10.1.
Tidak ada data pengguna / isi dokumen di sini.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class University(Base):
    """Daftar kampus untuk preset (§10.1)."""
    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)

    presets: Mapped[list["RulePreset"]] = relationship("RulePreset", back_populates="university")


class RuleGroup(Base):
    """Katalog 12 bagian aturan beserta dependensi (§10.1)."""
    __tablename__ = "rule_groups"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    urutan: Mapped[int] = mapped_column(Integer, nullable=False)
    depends_on: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bundle_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class RulePreset(Base):
    """Induk preset bawaan dan preset kampus (§10.1)."""
    __tablename__ = "rule_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    university_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("universities.id"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    jenjang_fakultas: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    versi: Mapped[str] = mapped_column(String(50), nullable=False)
    sumber_pedoman: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diverifikasi_pada: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    university: Mapped[Optional["University"]] = relationship("University", back_populates="presets")
    groups: Mapped[list["RulePresetGroup"]] = relationship(
        "RulePresetGroup", back_populates="preset", cascade="all, delete-orphan"
    )


class RulePresetGroup(Base):
    """Aturan per bagian dalam satu preset (§10.1)."""
    __tablename__ = "rule_preset_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[int] = mapped_column(Integer, ForeignKey("rule_presets.id"), nullable=False)
    group_key: Mapped[str] = mapped_column(String(50), nullable=False)
    rules_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    diatur: Mapped[bool] = mapped_column(Boolean, default=True, comment="false jika pedoman tidak mengatur bagian ini")

    preset: Mapped["RulePreset"] = relationship("RulePreset", back_populates="groups")


class CitationStyle(Base):
    """Konfigurasi gaya sitasi (§10.1)."""
    __tablename__ = "citation_styles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class KeywordDictionary(Base):
    """Kamus deteksi bab/subbab per jenis dokumen (§10.1)."""
    __tablename__ = "keyword_dictionary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    peran: Mapped[str] = mapped_column(String(50), nullable=False)
    kata_kunci: Mapped[str] = mapped_column(String(200), nullable=False)
    bahasa: Mapped[str] = mapped_column(String(10), default="id")


class UsageStat(Base):
    """Statistik anonim penggunaan – tanpa isi dokumen (§10.1)."""
    __tablename__ = "usage_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tanggal: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mode_standar: Mapped[str] = mapped_column(String(20), nullable=False)  # satu|campuran|acuan
    jumlah_bagian_diganti: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success|error
    durasi_ms: Mapped[int] = mapped_column(Integer, default=0)
    ai_dipakai: Mapped[bool] = mapped_column(Boolean, default=False)
    jumlah_temuan: Mapped[int] = mapped_column(Integer, default=0)


class ErrorLog(Base):
    """Log teknis tanpa isi dokumen (§10.1)."""
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    waktu: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    kode_error: Mapped[str] = mapped_column(String(100), nullable=False)
    tahap: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
