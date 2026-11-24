"""
app/services/reference_extractor.py
Ekstraksi aturan format dari dokumen acuan DOCX (PRD §FR-03, Tahap B).
Membaca: style, margin, font, spasi, heading, penomoran, sitasi, pustaka.
File acuan dihapus segera setelah ekstraksi.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from docx import Document
from docx.shared import Cm, Pt


def _pt_to_cm(pt: Optional[float]) -> Optional[float]:
    return round(pt / 28.35, 2) if pt else None


def _emu_to_cm(emu: Optional[int]) -> Optional[float]:
    return round(emu / 914400 * 2.54, 2) if emu else None


class ReferenceExtractor:
    """
    Membaca dokumen acuan DOCX dan mengekstrak aturan per bagian
    beserta skor keyakinan.
    """

    def extract(self, path: Path) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Returns:
            rules_per_group: Dict[group_key -> rules_dict]
            confidence_per_group: Dict[group_key -> float 0-1]
        """
        try:
            doc = Document(str(path))
        except Exception as e:
            raise ValueError(f"Gagal membuka dokumen acuan: {e}") from e

        rules: Dict[str, Any] = {}
        confidence: Dict[str, float] = {}

        # ----- Halaman & Margin -----
        section = doc.sections[0]
        margin_rules: Dict[str, Any] = {}
        if section.left_margin:
            margin_rules["margin_kiri_cm"] = _emu_to_cm(section.left_margin)
        if section.top_margin:
            margin_rules["margin_atas_cm"] = _emu_to_cm(section.top_margin)
        if section.right_margin:
            margin_rules["margin_kanan_cm"] = _emu_to_cm(section.right_margin)
        if section.bottom_margin:
            margin_rules["margin_bawah_cm"] = _emu_to_cm(section.bottom_margin)
        if margin_rules:
            rules["halaman"] = margin_rules
            confidence["halaman"] = 0.95

        # ----- Tipografi -----
        tipografi = self._extract_typography(doc)
        if tipografi:
            rules["tipografi"] = tipografi
            confidence["tipografi"] = 0.85

        # ----- Heading -----
        heading_rules = self._extract_heading_styles(doc)
        if heading_rules:
            rules["heading_bab"] = heading_rules
            confidence["heading_bab"] = 0.80

        # ----- Penomoran Halaman -----
        page_num = self._extract_page_numbering(doc)
        if page_num:
            rules["penomoran_halaman"] = page_num
            confidence["penomoran_halaman"] = 0.70

        # ----- Sitasi (heuristik dari pola teks) -----
        sitasi = self._detect_citation_style(doc)
        if sitasi:
            rules["sitasi"] = sitasi
            rules["daftar_pustaka"] = {**sitasi, "hanging_indent_cm": 1.25}
            confidence["sitasi"] = 0.65
            confidence["daftar_pustaka"] = 0.65

        return rules, confidence

    # ----- Internal -----

    def _extract_typography(self, doc: Document) -> Dict[str, Any]:
        """Baca font dan spasi dari paragraf normal pertama."""
        for para in doc.paragraphs:
            if not para.text.strip():
                continue
            if para.style and "Normal" in para.style.name:
                runs = para.runs
                font_name = runs[0].font.name if runs and runs[0].font.name else "Times New Roman"
                font_size = runs[0].font.size.pt if runs and runs[0].font.size else 12
                line_spacing = None
                if para.paragraph_format.line_spacing:
                    ls = para.paragraph_format.line_spacing
                    # Bisa dalam EMU atau Pt; jika > 100 asumsikan EMU
                    if ls > 100:
                        line_spacing = round(ls / 240, 1)  # 240 = 1 baris tunggal
                    else:
                        line_spacing = round(float(ls), 1)
                return {
                    "font": font_name,
                    "ukuran_pt": int(font_size),
                    "spasi": line_spacing or 1.5,
                    "justify": para.paragraph_format.alignment == 3,  # WD_ALIGN=JUSTIFY
                }
        return {}

    def _extract_heading_styles(self, doc: Document) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for para in doc.paragraphs:
            if not para.text.strip():
                continue
            style = para.style.name if para.style else ""
            if "Heading 1" in style and "h1_ukuran_pt" not in result:
                runs = para.runs
                size = runs[0].font.size.pt if runs and runs[0].font.size else 14
                result["h1_ukuran_pt"] = int(size)
                result["h1_tengah"] = para.paragraph_format.alignment == 1  # CENTER

            if "Heading 2" in style and "h2_format" not in result:
                result["h2_format"] = "{bab}.{sub}"

        # Deteksi pola penomoran romawi vs arab dari teks
        for para in doc.paragraphs:
            text = para.text.strip().upper()
            if re.match(r"^BAB\s+[IVXLCDM]+\b", text):
                result["penomoran"] = "romawi"
                break
            if re.match(r"^BAB\s+\d+\b", text):
                result["penomoran"] = "arab"
                break

        return result

    def _extract_page_numbering(self, doc: Document) -> Dict[str, Any]:
        """Heuristik dari header/footer section."""
        result: Dict[str, Any] = {}
        for section in doc.sections:
            # Footer
            if section.footer and section.footer.paragraphs:
                for para in section.footer.paragraphs:
                    if para.text.strip():
                        result["front"] = {
                            "format": "lower-roman",
                            "posisi": "bottom-center",
                        }
                        break
            # Header
            if section.header and section.header.paragraphs:
                for para in section.header.paragraphs:
                    if para.text.strip():
                        result["main"] = {
                            "format": "arabic",
                            "halaman_lain": "top-right",
                        }
                        break
        return result

    def _detect_citation_style(self, doc: Document) -> Optional[Dict[str, Any]]:
        """Deteksi gaya sitasi dari pola dalam teks."""
        apa_pattern = re.compile(r"\([A-Z][a-z]+,\s+\d{4}\)")  # (Penulis, 2024)
        ieee_pattern = re.compile(r"\[\d+\]")                   # [1]

        apa_count = 0
        ieee_count = 0

        for para in doc.paragraphs:
            text = para.text
            apa_count += len(apa_pattern.findall(text))
            ieee_count += len(ieee_pattern.findall(text))

        if apa_count == 0 and ieee_count == 0:
            return None
        if apa_count >= ieee_count:
            return {"gaya": "APA7", "batas_kutipan_blok": 40}
        return {"gaya": "IEEE", "batas_kutipan_blok": 40}
