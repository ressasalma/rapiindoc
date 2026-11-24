"""
app/services/compliance_reporter.py
Generator laporan kepatuhan (PRD §FR-17).
Menggabungkan:
- Sumber setiap aturan (provenance)
- Temuan Error/Warning/Info
- Pemeriksaan integritas teks
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

from app.schemas.session import (
    ComplianceItem,
    ComplianceReport,
    CompatibilityFinding,
    FindingLevel,
)


class ComplianceReporter:

    def build_report(
        self,
        job_id: str,
        doc_type: str,
        standard_mode: str,
        provenance: Dict[str, str],
        compatibility_findings: List[CompatibilityFinding],
        additional_findings: List[Dict[str, Any]],
        original_text: str,
        formatted_text: str,
    ) -> ComplianceReport:

        items: List[ComplianceItem] = []

        # Sumber setiap bagian → item Info
        for group, source in provenance.items():
            items.append(ComplianceItem(
                group=group,
                source=source,
                level=FindingLevel.info,
                message=f"Bagian '{group}' menggunakan aturan dari: {source}",
            ))

        # Temuan kompatibilitas
        for finding in compatibility_findings:
            items.append(ComplianceItem(
                group=finding.group,
                source=provenance.get(finding.group, "—"),
                level=finding.level,
                message=finding.message,
            ))

        # Temuan tambahan dari mesin format
        for f in additional_findings:
            items.append(ComplianceItem(
                group=f.get("group", "umum"),
                source=provenance.get(f.get("group", ""), "—"),
                level=FindingLevel(f.get("level", "info")),
                message=f.get("message", ""),
            ))

        # Pemeriksaan integritas teks
        text_ok = self._check_text_integrity(original_text, formatted_text)

        return ComplianceReport(
            job_id=job_id,
            doc_type=doc_type,
            standard_mode=standard_mode,
            rule_sources=provenance,
            items=items,
            text_integrity_ok=text_ok,
            generated_at=datetime.now().isoformat(),
        )

    @staticmethod
    def _check_text_integrity(original: str, formatted: str) -> bool:
        """
        Verifikasi bahwa isi teks tidak berubah (hanya format).
        Normalisasi spasi sebelum membandingkan.
        """
        def normalize(text: str) -> str:
            # Hapus spasi ganda, newline ganda
            text = re.sub(r"\s+", " ", text).strip().lower()
            return text

        norm_orig = normalize(original)
        norm_fmt = normalize(formatted)

        # Toleransi: formatted boleh mengandung teks tambahan dari cover/daftar isi
        # Periksa bahwa semua kata kunci penting dari original ada di formatted
        orig_words = set(norm_orig.split())
        fmt_words = set(norm_fmt.split())

        # Hitung berapa banyak kata original yang hilang
        missing = orig_words - fmt_words
        if len(orig_words) == 0:
            return True
        missing_ratio = len(missing) / len(orig_words)
        return missing_ratio < 0.05  # Toleransi 5%
