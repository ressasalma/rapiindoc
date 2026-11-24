"""
app/services/job_processor.py
Orkestrator pemrosesan job secara berurutan (Tahap A–J PRD §8.1).
Berjalan di thread background (atau dapat diadaptasi ke worker/antrean).
"""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.schemas.session import (
    CoverData,
    DocumentBlock,
    JobStatus,
    RuleProfile,
    StandardMode,
)
from app.services.ai_classifier import AIClassifier
from app.services.compliance_reporter import ComplianceReporter
from app.services.document_parser import DocumentParser
from app.services.file_manager import file_manager
from app.services.format_engine import FormatEngine
from app.services.reference_extractor import ReferenceExtractor
from app.services.rule_engine import RuleEngine
from app.services.session_store import session_store


class JobProcessor:
    """
    Memproses satu job dari ingest sampai ekspor.
    """

    def __init__(self):
        self._parser = DocumentParser()
        self._extractor = ReferenceExtractor()
        self._rule_engine = RuleEngine(preset_loader=self._load_preset_from_db)
        self._ai = AIClassifier()
        self._reporter = ComplianceReporter()

    # ----- Public API -----

    def start(self, job_id: str) -> None:
        """Jalankan job di thread terpisah."""
        t = threading.Thread(target=self._run, args=(job_id,), daemon=True)
        t.start()

    # ----- Pipeline -----

    def _run(self, job_id: str) -> None:
        start_time = time.time()
        try:
            job = session_store.get(job_id)
            if not job:
                return
            self._process(job_id, job)
        except Exception as e:
            logger.error("job_failed", job_id=job_id, error=str(e), exc_info=True)
            session_store.update(job_id, {
                "status": JobStatus.error,
                "error_message": str(e),
                "progress_pct": 0,
            })
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            self._record_stats(job_id, duration_ms)

    def _process(self, job_id: str, job: Dict[str, Any]) -> None:
        job_dir = file_manager.get_job_dir(job_id)
        if not job_dir:
            raise FileNotFoundError(f"Direktori job tidak ditemukan: {job_id}")

        profile_data = job.get("rule_profile")
        if isinstance(profile_data, dict):
            profile = RuleProfile(**profile_data)
        else:
            profile = profile_data or RuleProfile(doc_type=job["doc_type"])

        # ----- Tahap B: Ekstraksi aturan dokumen acuan -----
        ref_path = self._find_reference_file(job_id)
        if ref_path:
            self._update_status(job_id, JobStatus.extracting, 10)
            ref_rules, ref_confidence = self._extractor.extract(ref_path)
            # Simpan ke sesi untuk dipakai mesin aturan
            session_store.update(job_id, {
                "ref_rules": ref_rules,
                "ref_confidence": ref_confidence,
            })
            # Hapus file acuan setelah ekstraksi
            file_manager.delete_reference(job_id)
            logger.info("reference_extracted", job_id=job_id, groups=list(ref_rules.keys()))

        # ----- Tahap C: Komposisi standar -----
        self._update_status(job_id, JobStatus.composing, 20)
        resolved_rules, provenance = self._rule_engine.resolve(profile)
        compatibility = self._rule_engine.check_compatibility(profile, resolved_rules, provenance)
        session_store.update(job_id, {
            "resolved_rules": resolved_rules,
            "provenance": provenance,
            "compatibility": compatibility.model_dump(),
        })

        # ----- Tahap D: Parsing dokumen -----
        self._update_status(job_id, JobStatus.parsing, 35)
        input_path = self._find_input_file(job_id)
        raw_text = ""
        if input_path and input_path.suffix.lower() == ".docx":
            blocks, cover_data, raw_texts = self._parser.parse_docx(input_path)
            raw_text = "\n".join(raw_texts)
        elif job.get("pasted_text"):
            blocks, cover_data, raw_texts = self._parser.parse_text(job["pasted_text"])
            raw_text = job["pasted_text"]
        else:
            raise ValueError("Tidak ada dokumen input yang ditemukan.")

            logo_path = job.get("logo_path")
            if logo_path:
                cover_data.logo_url = logo_path
            session_store.update(job_id, {
                "blocks": [b.model_dump() for b in blocks],
                "cover_data": cover_data.model_dump(),
                "raw_text": raw_text,
            })

        # ----- Tahap E: AI untuk blok ambigu -----
        self._update_status(job_id, JobStatus.ai_classifying, 50)
        blocks = self._ai.classify_ambiguous(blocks)
        session_store.update(job_id, {
            "blocks": [b.model_dump() for b in blocks],
        })

        # ----- Tahap F: Tunggu review pengguna -----
        self._update_status(job_id, JobStatus.awaiting_review, 60)
        # Pipeline berhenti di sini; dilanjutkan oleh submit_review()

    def submit_review(
        self,
        job_id: str,
        corrected_blocks: List[DocumentBlock],
        cover_data: CoverData,
        updated_profile: Optional[RuleProfile] = None,
    ) -> None:
        """Dipanggil setelah pengguna selesai review outline dan cover."""
        job = session_store.get(job_id)
        if not job:
            raise ValueError(f"Job tidak ditemukan: {job_id}")

        session_store.update(job_id, {
            "blocks": [b.model_dump() for b in corrected_blocks],
            "cover_data": cover_data.model_dump(),
        })

        if updated_profile:
            # Re-resolve jika profil diubah
            resolved_rules, provenance = self._rule_engine.resolve(updated_profile)
            session_store.update(job_id, {
                "resolved_rules": resolved_rules,
                "provenance": provenance,
            })

        # Lanjutkan pipeline di thread
        t = threading.Thread(target=self._apply_format, args=(job_id,), daemon=True)
        t.start()

    def _apply_format(self, job_id: str) -> None:
        """Tahap G–J: Penerapan format, render, validasi, pengiriman."""
        try:
            job = session_store.get(job_id)
            if not job:
                return

            # ----- Tahap G: Penerapan format -----
            self._update_status(job_id, JobStatus.formatting, 70)
            blocks = [DocumentBlock(**b) for b in job["blocks"]]
            cover_data = CoverData(**job["cover_data"])
            resolved_rules = job.get("resolved_rules", {})
            provenance = job.get("provenance", {})

            engine = FormatEngine(resolved_rules, provenance)
            output_docx = file_manager.output_path(job_id, "output.docx")
            engine.build_document(blocks, cover_data, output_docx)

            # ----- Tahap H: Render PDF (opsional, LibreOffice) -----
            self._update_status(job_id, JobStatus.rendering, 85)
            pdf_path = self._render_pdf(job_id, output_docx)

            # ----- Tahap I: Validasi dan laporan -----
            self._update_status(job_id, JobStatus.validating, 92)
            formatted_text = self._extract_text_from_docx(output_docx)
            compatibility_data = job.get("compatibility", {})
            compat_findings = []

            report = self._reporter.build_report(
                job_id=job_id,
                doc_type=job.get("doc_type", ""),
                standard_mode=job.get("standard_mode", ""),
                provenance=provenance,
                compatibility_findings=compat_findings,
                additional_findings=[],
                original_text=job.get("raw_text", ""),
                formatted_text=formatted_text,
            )

            # ----- Tahap J: Siap diunduh -----
            download_files = {"docx": "output.docx"}
            if pdf_path:
                download_files["pdf"] = "output.pdf"

            session_store.update(job_id, {
                "status": JobStatus.done,
                "progress_pct": 100,
                "download_files": download_files,
                "compliance_report": report.model_dump(),
                "text_integrity_ok": report.text_integrity_ok,
            })
            logger.info("job_done", job_id=job_id)

        except Exception as e:
            logger.error("format_failed", job_id=job_id, error=str(e), exc_info=True)
            session_store.update(job_id, {
                "status": JobStatus.error,
                "error_message": str(e),
            })

    # ----- Helpers -----

    def _update_status(self, job_id: str, status: JobStatus, pct: int) -> None:
        session_store.update(job_id, {"status": status, "progress_pct": pct})

    def _find_input_file(self, job_id: str) -> Optional[Path]:
        input_dir = file_manager.input_path(job_id, "")
        for ext in (".docx", ".txt"):
            candidates = list(input_dir.parent.glob(f"*{ext}")) if input_dir.parent.exists() else []
            if candidates:
                return candidates[0]
        # Cari di sub-folder input
        input_folder = file_manager.get_job_dir(job_id)
        if input_folder:
            for f in (input_folder / "input").iterdir():
                return f
        return None

    def _find_reference_file(self, job_id: str) -> Optional[Path]:
        ref_dir = file_manager.get_job_dir(job_id)
        if ref_dir:
            ref_folder = ref_dir / "reference"
            if ref_folder.exists():
                files = list(ref_folder.iterdir())
                if files:
                    return files[0]
        return None

    def _render_pdf(self, job_id: str, docx_path: Path) -> Optional[Path]:
        """Konversi DOCX ke PDF secara opsional dengan timeout singkat 5s."""
        from app.core.config import settings
        import subprocess
        pdf_path = file_manager.output_path(job_id, "output.pdf")
        try:
            result = subprocess.run(
                [
                    settings.libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(docx_path.parent),
                    str(docx_path),
                ],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                generated = docx_path.parent / (docx_path.stem + ".pdf")
                if generated.exists() and generated != pdf_path:
                    generated.rename(pdf_path)
                return pdf_path if pdf_path.exists() else None
        except Exception:
            return None
        return None

    @staticmethod
    def _extract_text_from_docx(docx_path: Path) -> str:
        """Ekstrak teks plain dari DOCX untuk verifikasi integritas."""
        try:
            from docx import Document
            doc = Document(str(docx_path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""

    @staticmethod
    def _load_preset_from_db(preset_slug: str, doc_type: str) -> Optional[Dict[str, Any]]:
        """
        Muat aturan preset dari MySQL (§10.1).
        Menggunakan import lazy untuk menghindari circular dependency.
        """
        try:
            from app.db.database import SessionLocal
            from app.models.system import RulePreset, University
            from sqlalchemy import select

            with SessionLocal() as db:
                stmt = (
                    select(RulePreset)
                    .join(University, isouter=True)
                    .where(
                        University.slug == preset_slug,
                        RulePreset.doc_type == doc_type,
                    )
                    .limit(1)
                )
                preset = db.execute(stmt).scalar_one_or_none()
                if not preset:
                    return None
                result: Dict[str, Any] = {}
                for group in preset.groups:
                    if group.diatur:
                        result[group.group_key] = group.rules_json
                return result
        except Exception as e:
            logger.warning("preset_load_failed", slug=preset_slug, error=str(e))
            return None

    def _record_stats(self, job_id: str, duration_ms: int) -> None:
        """Catat statistik anonim ke MySQL (§10.1)."""
        job = session_store.get(job_id)
        if not job:
            return
        try:
            from app.db.database import SessionLocal
            from app.models.system import UsageStat

            stat = UsageStat(
                doc_type=job.get("doc_type", "unknown"),
                mode_standar=job.get("standard_mode", "satu"),
                jumlah_bagian_diganti=job.get("sources_overridden", 0),
                status="success" if job.get("status") == JobStatus.done else "error",
                durasi_ms=duration_ms,
                ai_dipakai=job.get("ai_used", False),
                jumlah_temuan=len(job.get("compliance_report", {}).get("items", [])),
            )
            with SessionLocal() as db:
                db.add(stat)
                db.commit()
        except Exception as e:
            logger.warning("stats_record_failed", job_id=job_id, error=str(e))


# Singleton
job_processor = JobProcessor()
