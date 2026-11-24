"""
app/services/document_parser.py
Parsing dokumen DOCX atau teks tempel menjadi pohon blok dengan peran
dan skor keyakinan (PRD §6).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.session import BlockRole, CoverData, DocumentBlock

# Kata kunci untuk deteksi peran (kamus bawaan; versi DB ada di keyword_dictionary)
ROLE_KEYWORDS: Dict[str, List[str]] = {
    BlockRole.kata_pengantar: ["kata pengantar"],
    BlockRole.abstrak: ["abstrak", "abstract"],
    BlockRole.daftar_isi: ["daftar isi"],
    BlockRole.daftar_tabel: ["daftar tabel"],
    BlockRole.daftar_gambar: ["daftar gambar"],
    BlockRole.lembar_pengesahan: ["lembar pengesahan", "halaman pengesahan"],
    BlockRole.daftar_pustaka: ["daftar pustaka", "referensi", "bibliography"],
    BlockRole.lampiran: ["lampiran"],
}

COVER_SIGNALS = [
    "makalah", "laporan", "proposal", "skripsi", "tesis", "disertasi",
    "disusun oleh", "nim", "nip", "universitas", "institut", "sekolah tinggi",
    "politeknik", "akademi", "fakultas", "program studi", "jurusan",
    "dosen pengampu", "pembimbing",
]

BAB_PATTERN = re.compile(
    r"^(bab\s+[ivxlcdm\d]+|chapter\s+\d+)\b",
    re.IGNORECASE,
)
SUBBAB_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)*\s+\S")
NUMBERED_HEADING = re.compile(r"^[A-Z]\.\s+\S|^[IVXLCDM]+\.\s+\S")
REFERENCE_LINE = re.compile(
    r"(\d{4})[\.)]|doi:|https?://|et al\.|jurnal|journal|vol\.|no\.",
    re.IGNORECASE,
)


def _make_block(role: BlockRole, text: str, confidence: float) -> DocumentBlock:
    return DocumentBlock(
        block_id=uuid.uuid4().hex[:12],
        role=role,
        confidence=confidence,
        is_ambiguous=confidence < 0.6,
        text_preview=text[:120],
        text_content=text,
    )


class DocumentParser:
    """
    Memecah DOCX atau teks plain menjadi pohon blok dengan peran
    dan skor keyakinan.
    """

    # ----- Entry Points -----

    def parse_docx(self, path: Path) -> Tuple[List[DocumentBlock], CoverData, List[str]]:
        """
        Parse file DOCX.
        Returns: (outline, cover_data, raw_texts)
        """
        try:
            from docx import Document
            doc = Document(str(path))
        except Exception as e:
            raise ValueError(f"Gagal membuka DOCX: {e}") from e

        raw_texts: List[str] = []
        paragraphs: List[Dict[str, Any]] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            raw_texts.append(text)
            paragraphs.append({
                "text": text,
                "style": para.style.name if para.style else "",
                "bold": any(run.bold for run in para.runs if run.bold),
                "font_size": self._max_font_size(para),
            })

        blocks, cover_data = self._classify_paragraphs(paragraphs)
        return blocks, cover_data, raw_texts

    def parse_text(self, text: str) -> Tuple[List[DocumentBlock], CoverData, List[str]]:
        """
        Parse teks tempel (Markdown-ish atau plain).
        Returns: (outline, cover_data, raw_texts)
        """
        lines = [line.rstrip() for line in text.splitlines()]
        raw_texts = [line for line in lines if line.strip()]
        paragraphs = [self._para_from_text(line) for line in raw_texts if line.strip() != "---"]

        blocks, cover_data = self._classify_paragraphs(paragraphs)
        return blocks, cover_data, raw_texts

    # ----- Klasifikasi -----

    def _classify_paragraphs(
        self, paragraphs: List[Dict[str, Any]]
    ) -> Tuple[List[DocumentBlock], CoverData]:
        blocks: List[DocumentBlock] = []
        cover_lines: List[str] = []
        cover_found = False
        cover_data = CoverData()

        for i, para in enumerate(paragraphs):
            text = para["text"]
            role, confidence = self._detect_role(para, i, len(paragraphs))

            if role == BlockRole.cover and not cover_found:
                cover_lines.append(text)
                cover_found = True
                blocks.append(_make_block(role, text, confidence))
                continue

            # Kumpulkan sinyal cover di awal dokumen
            if not cover_found and i < 15 and self._is_cover_signal(text):
                cover_lines.append(text)
                blocks.append(_make_block(BlockRole.cover, text, 0.75))
                continue

            blocks.append(_make_block(role, text, confidence))

        if cover_lines:
            cover_data = self._extract_cover_data(cover_lines)

        return blocks, cover_data

    def _detect_role(
        self, para: Dict[str, Any], idx: int, total: int
    ) -> Tuple[BlockRole, float]:
        text = para["text"]
        lower = text.lower()
        style = para.get("style", "")
        bold = para.get("bold", False)
        font_size = para.get("font_size", 12)

        # Heading dari style Word
        if re.match(r"^#{1,2}\s+", text) or "Heading 1" in style or style.startswith("heading 1"):
            return BlockRole.cover if idx < 3 else BlockRole.heading_bab, 0.98
        if re.match(r"^#{3}\s+", text) or "Heading 2" in style or style.startswith("heading 2"):
            return BlockRole.heading_bab if "bab " in lower else BlockRole.heading_subbab, 0.95
        if re.match(r"^#{4,6}\s+", text) or "Heading 3" in style or style.startswith("heading 3"):
            return BlockRole.heading_subbab, 0.92

        # Pola BAB
        if BAB_PATTERN.match(lower):
            return BlockRole.heading_bab, 0.95

        # Pola subbab berformat "1.1 Judul"
        if SUBBAB_PATTERN.match(text):
            return BlockRole.heading_subbab, 0.88
        if re.match(r"^\s*(\d+\.|[-*+])\s+", text):
            return BlockRole.paragraf, 0.90
        if text.startswith("|"):
            return BlockRole.tabel, 0.90

        # Kata kunci spesifik
        for role, keywords in ROLE_KEYWORDS.items():
            for kw in keywords:
                if lower.strip() == kw or lower.startswith(kw):
                    return role, 0.90

        # Daftar pustaka (pola baris referensi)
        if idx > total * 0.7 and REFERENCE_LINE.search(lower):
            return BlockRole.daftar_pustaka, 0.72

        # Teks panjang dengan banyak kata → paragraf
        word_count = len(text.split())
        if word_count > 20:
            return BlockRole.paragraf, 0.80

        # Baris pendek, cetak tebal, atau font besar → heading ambigu
        if (bold or font_size > 12) and word_count <= 15:
            return BlockRole.unknown, 0.50

        return BlockRole.paragraf, 0.65

    @staticmethod
    def _is_cover_signal(text: str) -> bool:
        lower = text.lower()
        return any(sig in lower for sig in COVER_SIGNALS)

    # ----- Ekstraksi Data Cover -----

    def _extract_cover_data(self, lines: List[str]) -> CoverData:
        data: Dict[str, Any] = {}
        confidence_total = 0.0
        n = 0

        for line in lines:
            lower = line.lower()

            if "nim" in lower or "nip" in lower:
                match = re.search(r"\b(?:nim|nip)\b\s*[:;]?\s*([A-Za-z0-9./-]+)", line, re.IGNORECASE)
                if match:
                    data["nim"] = match.group(1)
                    confidence_total += 0.9
                    n += 1
                continue

            if not data.get("judul") and len(line) > 10 and line.isupper():
                data["judul"] = line
                confidence_total += 0.8
                n += 1
                continue

            if "nim" in lower or "nip" in lower:
                match = re.search(r"\b(?:nim|nip)\b\s*[:;]?\s*([A-Za-z0-9./-]+)", line, re.IGNORECASE)
                if match:
                    data["nim"] = match.group(1)
                    confidence_total += 0.9
                    n += 1
                continue

            if "disusun oleh" in lower or "penulis" in lower:
                parts = re.split(r"[:;]", line, maxsplit=1)
                if len(parts) == 2:
                    data["nama_penulis"] = parts[1].strip()
                    confidence_total += 0.85
                    n += 1
                continue

            if "dosen" in lower or "pembimbing" in lower or "pengampu" in lower:
                parts = re.split(r"[:;]", line, maxsplit=1)
                if len(parts) == 2:
                    data["dosen_pengampu"] = parts[1].strip()
                confidence_total += 0.8
                n += 1
                continue

            if "program studi" in lower or "jurusan" in lower:
                parts = re.split(r"[:;]", line, maxsplit=1)
                data["program_studi"] = parts[-1].strip()
                confidence_total += 0.8
                n += 1
                continue

            if "fakultas" in lower:
                parts = re.split(r"[:;]", line, maxsplit=1)
                data["fakultas"] = parts[-1].strip()
                confidence_total += 0.8
                n += 1
                continue

            # Universitas / kampus
            for kw in ["universitas", "institut", "sekolah tinggi", "politeknik", "akademi"]:
                if kw in lower:
                    data["institusi"] = line
                    confidence_total += 0.75
                    n += 1
                    break

            # Tahun (4 digit)
            year_match = re.search(r"\b(20\d{2}|19\d{2})\b", line)
            if year_match and not data.get("tahun"):
                data["tahun"] = year_match.group()
                confidence_total += 0.9
                n += 1

        return CoverData(
            **data,
            confidence=round(confidence_total / n, 2) if n else 0.0,
        )

    # ----- Helpers -----

    @staticmethod
    def _max_font_size(para) -> int:
        sizes = [
            run.font.size.pt
            for run in para.runs
            if run.font and run.font.size
        ]
        return int(max(sizes)) if sizes else 12

    @staticmethod
    def _para_from_text(text: str) -> Dict[str, Any]:
        text = re.sub(r"[*_#`~]+", "", text).strip()
        return {"text": text, "style": "", "bold": False, "font_size": 12}
