"""
app/api/routes_session.py
Endpoint: sesi, job, upload, review, unduh, hapus.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    generate_job_id,
    generate_session_token,
    sign_download_url,
    verify_download_token,
)
from app.schemas.session import (
    CoverData,
    DownloadLink,
    JobCreateRequest,
    JobStatus,
    JobStatusResponse,
    ReviewSubmit,
    RuleProfile,
    SessionCreateResponse,
)
from app.services.file_manager import file_manager
from app.services.job_processor import job_processor
from app.services.session_store import session_store

router = APIRouter(prefix="/api/v1", tags=["session"])

# ----- Allowed MIME types -----
ALLOWED_MIME = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
ALLOWED_EXT = {".docx"}


# ============================================================
# 1. Sesi (FR-01)
# ============================================================

@router.post("/session", response_model=SessionCreateResponse)
def create_session():
    """Buat sesi anonim baru. Tidak ada login diperlukan."""
    token = generate_session_token()
    return SessionCreateResponse(
        session_token=token,
        expires_in_seconds=settings.file_ttl_minutes * 60,
    )


# ============================================================
# 2. Job – Buat (FR-02, FR-04, FR-05)
# ============================================================

@router.post("/jobs", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    req: JobCreateRequest,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """
    Buat job baru dengan jenis dokumen, mode standar, dan Profil Aturan opsional.
    """
    job_id = generate_job_id()
    file_manager.create_job_dir(job_id)

    job_data = {
        "job_id": job_id,
        "session_token": x_session_token,
        "doc_type": req.doc_type,
        "standard_mode": req.standard_mode,
        "rule_profile": req.rule_profile.model_dump(by_alias=True) if req.rule_profile else None,
        "status": JobStatus.pending,
        "progress_pct": 0,
        "error_message": None,
    }
    session_store.set(job_id, job_data, ttl=settings.file_ttl_minutes * 60)

    logger.info("job_created", job_id=job_id, doc_type=req.doc_type, mode=req.standard_mode)
    return JobStatusResponse(job_id=job_id, status=JobStatus.pending)


# ============================================================
# 3. Upload Dokumen Utama (FR-09)
# ============================================================

@router.post("/jobs/{job_id}/upload", response_model=JobStatusResponse)
async def upload_document(
    job_id: str,
    file: Optional[UploadFile] = File(None),
    logo: Optional[UploadFile] = File(None),
    pasted_text: Optional[str] = Form(None),
    x_session_token: str = Header(..., alias="X-Session-Token"),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload DOCX atau kirim teks tempel.
    Memulai pipeline pemrosesan di background.
    """
    _verify_job_session(job_id, x_session_token)

    if file is None and not pasted_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Harap unggah file DOCX atau masukkan teks.",
        )

    if file:
        _validate_file(file)
        input_path = file_manager.input_path(job_id, f"input{Path(file.filename).suffix}")
        content = await file.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Ukuran file melebihi batas {settings.max_file_size // (1024*1024)} MB.",
            )
        input_path.write_bytes(content)
        logger.info("file_uploaded", job_id=job_id, size=len(content))
    else:
        session_store.update(job_id, {"pasted_text": pasted_text})

    if logo:
        logo_path = file_manager.input_path(job_id, "logo" + Path(logo.filename or "logo.png").suffix)
        logo_path.write_bytes(await logo.read())
        session_store.update(job_id, {"logo_path": str(logo_path)})

    # Ambil profil dari sesi dan mulai pipeline
    job = session_store.get(job_id)
    profile_data = job.get("rule_profile")
    rule_profile = RuleProfile(**profile_data) if profile_data else None

    session_store.update(job_id, {
        "rule_profile": rule_profile.model_dump(by_alias=True) if rule_profile else None,
    })

    job_processor.start(job_id)

    return JobStatusResponse(job_id=job_id, status=JobStatus.pending, progress_pct=5)


# ============================================================
# 4. Upload Dokumen Acuan (FR-03)
# ============================================================

@router.post("/jobs/{job_id}/reference", response_model=dict)
async def upload_reference(
    job_id: str,
    file: UploadFile = File(...),
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """
    Upload dokumen acuan DOCX.
    File dihapus segera setelah aturan diekstrak.
    """
    _verify_job_session(job_id, x_session_token)
    _validate_file(file)

    ref_path = file_manager.reference_path(job_id, f"reference{Path(file.filename).suffix}")
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=413, detail="File acuan terlalu besar.")
    ref_path.write_bytes(content)

    # Ekstrak segera
    from app.services.reference_extractor import ReferenceExtractor
    extractor = ReferenceExtractor()
    try:
        ref_rules, ref_confidence = extractor.extract(ref_path)
        file_manager.delete_reference(job_id)  # Hapus segera
        return {"extracted_groups": list(ref_rules.keys()), "confidence": ref_confidence}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# 5. Status Job (FR-11)
# ============================================================

@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """Ambil status job dan data outline/cover (tersedia saat awaiting_review)."""
    job = _verify_job_session(job_id, x_session_token)

    response = JobStatusResponse(
        job_id=job_id,
        status=JobStatus(job["status"]),
        progress_pct=job.get("progress_pct", 0),
        error_message=job.get("error_message"),
    )

    # Sertakan outline dan cover saat menunggu review
    if job["status"] == JobStatus.awaiting_review:
        from app.schemas.session import DocumentBlock
        raw_blocks = job.get("blocks", [])
        cover_raw = job.get("cover_data", {})
        response.outline = [DocumentBlock(**b) for b in raw_blocks]
        response.cover_data = CoverData(**cover_raw) if cover_raw else None

    # Sertakan temuan kompatibilitas
    compat_raw = job.get("compatibility")
    if compat_raw:
        from app.schemas.session import CompatibilityResult
        response.compatibility = CompatibilityResult(**compat_raw)

    return response


# ============================================================
# 6. Submit Review (FR-11)
# ============================================================

@router.post("/jobs/{job_id}/review", response_model=JobStatusResponse)
def submit_review(
    job_id: str,
    body: ReviewSubmit,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """
    Pengguna mengirim koreksi outline dan cover.
    Pipeline dilanjutkan ke Tahap G (penerapan format).
    """
    job = _verify_job_session(job_id, x_session_token)

    if job["status"] != JobStatus.awaiting_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job dalam status '{job['status']}', bukan 'awaiting_review'.",
        )

    job_processor.submit_review(
        job_id=job_id,
        corrected_blocks=body.corrected_outline,
        cover_data=body.cover_data,
        updated_profile=body.rule_profile,
    )
    return JobStatusResponse(job_id=job_id, status=JobStatus.formatting, progress_pct=65)


# ============================================================
# 7. Unduh Hasil (FR-19)
# ============================================================

@router.get("/jobs/{job_id}/download/{format}", response_class=FileResponse)
def download_result(
    job_id: str,
    format: str,
    expires: int,
    sig: str,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """
    Unduh hasil DOCX atau PDF menggunakan tautan bertanda waktu.
    """
    _verify_job_session(job_id, x_session_token)

    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Format tidak didukung.")

    filename = f"output.{format}"
    if not verify_download_token(job_id, filename, expires, sig):
        raise HTTPException(status_code=403, detail="Token unduhan tidak valid atau kedaluwarsa.")

    file_path = file_manager.output_path(job_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
    }
    return FileResponse(
        path=str(file_path),
        media_type=media_types[format],
        filename=f"rapiindoc_output.{format}",
    )


@router.get("/jobs/{job_id}/download-links", response_model=list[DownloadLink])
def get_download_links(
    job_id: str,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """Dapatkan tautan unduhan bertanda waktu untuk DOCX dan PDF."""
    job = _verify_job_session(job_id, x_session_token)

    if job.get("status") != JobStatus.done:
        raise HTTPException(status_code=409, detail="Job belum selesai.")

    import time
    links = []
    ttl = settings.file_ttl_minutes * 60
    expires_at = int(time.time()) + ttl

    for fmt, fname in job.get("download_files", {}).items():
        qs = sign_download_url(job_id, fname, ttl)
        links.append(DownloadLink(
            url=f"/api/v1/jobs/{job_id}/download/{fmt}?{qs}",
            format=fmt,
            expires_at=expires_at,
        ))

    return links


# ============================================================
# 8. Laporan Kepatuhan (FR-17)
# ============================================================

@router.get("/jobs/{job_id}/compliance")
def get_compliance_report(
    job_id: str,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """Ambil laporan kepatuhan dengan sumber aturan per bagian."""
    job = _verify_job_session(job_id, x_session_token)

    report = job.get("compliance_report")
    if not report:
        raise HTTPException(status_code=404, detail="Laporan belum tersedia.")
    return report


# ============================================================
# 9. Hapus Job (FR-20)
# ============================================================

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    x_session_token: str = Header(..., alias="X-Session-Token"),
):
    """Hapus semua file job sekarang (tombol 'Hapus sekarang')."""
    _verify_job_session(job_id, x_session_token)
    session_store.delete(job_id)
    file_manager.delete_job(job_id)
    logger.info("job_manually_deleted", job_id=job_id)


# ============================================================
# Helpers
# ============================================================

def _verify_job_session(job_id: str, session_token: str) -> dict:
    job = session_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan atau kedaluwarsa.")
    if job.get("session_token") != session_token:
        raise HTTPException(status_code=403, detail="Token sesi tidak sesuai.")
    return job


def _validate_file(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Format file '{suffix}' tidak didukung. Gunakan DOCX.",
        )
