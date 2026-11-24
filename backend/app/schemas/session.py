"""
app/schemas/session.py
Pydantic schemas untuk sesi dan job.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    makalah = "makalah"
    laporan = "laporan"
    proposal = "proposal"
    jurnal = "jurnal"
    lainnya = "lainnya"


class StandardMode(str, Enum):
    satu = "satu"           # Satu standar
    campuran = "campuran"   # Campuran per bagian
    acuan = "acuan"         # Dari dokumen acuan


class JobStatus(str, Enum):
    pending = "pending"
    extracting = "extracting"       # Tahap B: ekstraksi aturan acuan
    composing = "composing"         # Tahap C: komposisi standar
    parsing = "parsing"             # Tahap D: parsing dokumen
    ai_classifying = "ai_classifying"  # Tahap E: AI untuk ambigu
    awaiting_review = "awaiting_review"  # Tahap F: review pengguna
    formatting = "formatting"       # Tahap G: penerapan format
    rendering = "rendering"         # Tahap H: konversi PDF
    validating = "validating"       # Tahap I: validasi
    done = "done"
    error = "error"
    deleted = "deleted"


class FindingLevel(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


# ----- Session -----

class SessionCreateResponse(BaseModel):
    session_token: str
    expires_in_seconds: int = Field(default=1800)


# ----- Rule Profile -----

class RuleSource(BaseModel):
    """Satu sumber aturan untuk satu bagian."""
    from_: str = Field(alias="from")  # preset | bawaan | acuan | manual
    preset: Optional[str] = None
    versi: Optional[str] = None
    style: Optional[str] = None
    linked_to: Optional[str] = None
    confidence: Optional[float] = None

    model_config = {"populate_by_name": True}


class RuleOverride(BaseModel):
    """Override manual untuk satu aturan dalam satu bagian."""
    group_key: str
    rules: Dict[str, Any]


class RuleProfile(BaseModel):
    """
    Profil Aturan lengkap (JSON yang dapat diunduh/diunggah pengguna).
    Sesuai Lampiran A PRD.
    """
    doc_type: DocType
    base: Optional[Dict[str, Any]] = None   # {preset, versi}
    sources: Dict[str, RuleSource] = Field(default_factory=dict)
    overrides: Dict[str, Any] = Field(default_factory=dict)
    groups: Dict[str, Any] = Field(default_factory=dict)
    resolved_summary: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


# ----- Compatibility Check -----

class CompatibilityFinding(BaseModel):
    level: FindingLevel
    group: str
    message: str


class CompatibilityResult(BaseModel):
    findings: List[CompatibilityFinding]
    has_errors: bool
    has_warnings: bool


# ----- Cover Data -----

class CoverData(BaseModel):
    jenis_dokumen: Optional[str] = None
    judul: Optional[str] = None
    nama_penulis: Optional[str] = None
    nim: Optional[str] = None
    dosen_pengampu: Optional[str] = None
    program_studi: Optional[str] = None
    fakultas: Optional[str] = None
    institusi: Optional[str] = None
    kota: Optional[str] = None
    tahun: Optional[str] = None
    logo_url: Optional[str] = None
    confidence: float = 0.0


# ----- Document Block (Struktur Outline) -----

class BlockRole(str, Enum):
    cover = "cover"
    kata_pengantar = "kata_pengantar"
    abstrak = "abstrak"
    daftar_isi = "daftar_isi"
    daftar_tabel = "daftar_tabel"
    daftar_gambar = "daftar_gambar"
    lembar_pengesahan = "lembar_pengesahan"
    heading_bab = "heading_bab"
    heading_subbab = "heading_subbab"
    paragraf = "paragraf"
    daftar_pustaka = "daftar_pustaka"
    lampiran = "lampiran"
    tabel = "tabel"
    gambar = "gambar"
    caption = "caption"
    kutipan_blok = "kutipan_blok"
    unknown = "unknown"


class DocumentBlock(BaseModel):
    block_id: str
    role: BlockRole
    confidence: float = Field(ge=0.0, le=1.0)
    is_ambiguous: bool = False
    text_preview: str = ""
    text_content: str = ""
    children: List["DocumentBlock"] = Field(default_factory=list)


DocumentBlock.model_rebuild()


# ----- Job -----

class JobCreateRequest(BaseModel):
    doc_type: DocType
    standard_mode: StandardMode
    rule_profile: Optional[RuleProfile] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_pct: int = Field(ge=0, le=100, default=0)
    cover_data: Optional[CoverData] = None
    outline: Optional[List[DocumentBlock]] = None
    compatibility: Optional[CompatibilityResult] = None
    error_message: Optional[str] = None


class ReviewSubmit(BaseModel):
    """Pengguna mengirim koreksi outline dan cover sebelum format diterapkan."""
    corrected_outline: List[DocumentBlock]
    cover_data: CoverData
    rule_profile: Optional[RuleProfile] = None  # override profil di langkah ini


# ----- Compliance Report -----

class ComplianceItem(BaseModel):
    group: str
    source: str
    level: FindingLevel
    message: str


class ComplianceReport(BaseModel):
    job_id: str
    doc_type: str
    standard_mode: str
    rule_sources: Dict[str, str]        # group_key -> source label
    items: List[ComplianceItem]
    text_integrity_ok: bool
    generated_at: str


# ----- Download -----

class DownloadLink(BaseModel):
    url: str
    format: str                         # docx | pdf
    expires_at: int                     # unix timestamp
