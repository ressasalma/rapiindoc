"""
app/services/format_engine.py
Mesin penerapan format DOCX secara deterministik (PRD §FR-13, FR-14, FR-15).
Input: Profil Aturan final + pohon blok yang sudah dikoreksi pengguna.
Output: file DOCX terformat.
Prinsip: hanya format yang diubah, bukan isi.
"""

from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor, Inches
from lxml import etree

from app.schemas.session import BlockRole, CoverData, DocumentBlock


# =====================================================================
# Helpers OOXML
# =====================================================================

def _set_page_size_margin(section, rules_halaman: Dict[str, Any]) -> None:
    """Set ukuran kertas dan margin sesuai aturan."""
    # Ukuran A4
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(rules_halaman.get("margin_kiri_cm", 4.0))
    section.top_margin = Cm(rules_halaman.get("margin_atas_cm", 3.0))
    section.right_margin = Cm(rules_halaman.get("margin_kanan_cm", 3.0))
    section.bottom_margin = Cm(rules_halaman.get("margin_bawah_cm", 3.0))


def _apply_typography(para, rules_tipografi: Dict[str, Any]) -> None:
    """Terapkan tipografi pada paragraf."""
    pf = para.paragraph_format
    pf.line_spacing = Pt(rules_tipografi.get("ukuran_pt", 12) * rules_tipografi.get("spasi", 1.5))
    if rules_tipografi.get("justify", True):
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    indent_cm = rules_tipografi.get("indentasi_pertama_cm", 1.25)
    pf.first_line_indent = Cm(indent_cm)

    for run in para.runs:
        run.font.name = rules_tipografi.get("font", "Times New Roman")
        run.font.size = Pt(rules_tipografi.get("ukuran_pt", 12))
        run.font.color.rgb = RGBColor(0, 0, 0)


def _clear_manual_numbering(text: str) -> str:
    """Hapus penomoran manual yang diketik (mis. '1.1 ', 'BAB I ', 'A. ')."""
    text = re.sub(r"^(bab\s+[ivxlcdm\d]+\s*[:.]?\s*)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d+\.\d+(\.\d+)?\s+", "", text)
    return text.strip()


def _add_page_break(doc: Document) -> None:
    para = doc.add_paragraph()
    run = para.add_run()
    run.add_break(WD_BREAK.PAGE)


def _add_section_break(doc: Document) -> None:
    """Tambah section break (continuous) untuk penomoran halaman multi-seksi."""
    para = doc.add_paragraph()
    pPr = para._p.get_or_add_pPr()
    sectPr = OxmlElement("w:sectPr")
    pgSz = OxmlElement("w:pgSz")
    pgSz.set(qn("w:w"), "12240")   # 8.5 inch wide
    pgSz.set(qn("w:h"), "15840")   # 11 inch tall
    sectPr.append(pgSz)
    pPr.append(sectPr)


def _set_heading_style(para, level: int, rules_heading: Dict[str, Any]) -> None:
    """Set style heading sesuai aturan."""
    if level == 1:
        para.style = "Heading 1"
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(rules_heading.get("h1_ukuran_pt", 14))
            run.font.color.rgb = RGBColor(0, 0, 0)
    elif level == 2:
        para.style = "Heading 2"
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(0, 0, 0)
    elif level == 3:
        para.style = "Heading 3"
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in para.runs:
            run.bold = True
            run.italic = True
            run.font.size = Pt(12)


def _roman(n: int) -> str:
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]
    result = ""
    for v, s in zip(vals, syms):
        while n >= v:
            result += s
            n -= v
    return result


# =====================================================================
# Generator Bagian Dokumen
# =====================================================================

class FormatEngine:
    """
    Menerapkan format deterministik ke dokumen berdasarkan Profil Aturan.
    """

    def __init__(self, resolved_rules: Dict[str, Any], provenance: Dict[str, str]):
        self.rules = resolved_rules
        self.provenance = provenance
        self._bab_counter = 0
        self._bab_map: Dict[str, int] = {}  # block_id -> bab_number

    # ----- Entry Point -----

    def build_document(
        self,
        blocks: List[DocumentBlock],
        cover_data: CoverData,
        output_path: Path,
    ) -> Path:
        """
        Bangun DOCX terformat dari blok dan cover.
        Returns: path file output.
        """
        doc = Document()
        styles = doc.styles
        for style_name in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
            style = styles[style_name]
            style.font.name = "Times New Roman"
            style.font.color.rgb = RGBColor(0, 0, 0)

        # Setup halaman utama
        section = doc.sections[0]
        _set_page_size_margin(section, self.rules.get("halaman", {}))

        # 1. Cover
        self._build_cover(doc, cover_data)

        # 2. Bagian awal (kata pengantar, abstrak, daftar isi, dll.)
        self._build_front_matter(doc, blocks)

        # 3. Isi (bab-bab)
        self._build_body(doc, blocks)

        # 4. Daftar pustaka
        self._build_references(doc, blocks)

        # 5. Lampiran
        self._build_appendix(doc, blocks)

        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
        for section in doc.sections:
            footer = section.footer.paragraphs[0]
            footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = footer.add_run()
            fld = OxmlElement("w:fldSimple")
            fld.set(qn("w:instr"), "PAGE")
            run._r.append(fld)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = RGBColor(0, 0, 0)

        doc.save(str(output_path))
        return output_path

    # ----- Cover (§FR-10, §FR-14) -----

    def _build_cover(self, doc: Document, cover: CoverData) -> None:
        rules_cover = self.rules.get("cover", {})
        order = rules_cover.get("urutan", [
            "jenis_dokumen", "judul", "logo", "nama_nim",
            "dosen", "prodi", "fakultas", "institusi", "kota_tahun"
        ])

        def _center_bold(text: str, size: int = 12, all_caps: bool = False) -> None:
            if not text:
                return
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text.upper() if all_caps else text)
            run.bold = True
            run.font.size = Pt(size)
            run.font.name = "Times New Roman"

        def _center(text: str, size: int = 12) -> None:
            if not text:
                return
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.font.size = Pt(size)
            run.font.name = "Times New Roman"

        for item in order:
            if item == "jenis_dokumen" and cover.jenis_dokumen:
                _center_bold(cover.jenis_dokumen, size=14, all_caps=True)
            elif item == "judul" and cover.judul:
                _center_bold(cover.judul, size=14, all_caps=rules_cover.get("judul_kapital", True))
            elif item == "logo" and cover.logo_url and Path(cover.logo_url).exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(cover.logo_url, width=Inches(1.0))
            elif item == "nama_nim":
                if cover.nama_penulis:
                    _center(cover.nama_penulis)
                if cover.nim:
                    _center(f"NIM: {cover.nim}")
            elif item == "dosen" and cover.dosen_pengampu:
                _center(f"Dosen Pengampu/Pembimbing:")
                _center(cover.dosen_pengampu)
            elif item == "prodi" and cover.program_studi:
                _center(cover.program_studi)
            elif item == "fakultas" and cover.fakultas:
                _center(cover.fakultas)
            elif item == "institusi" and cover.institusi:
                _center_bold(cover.institusi)
            elif item == "kota_tahun":
                kota = cover.kota or ""
                tahun = cover.tahun or ""
                if kota or tahun:
                    _center(f"{kota} {tahun}".strip())

        # Page break setelah cover
        _add_page_break(doc)

    # ----- Bagian Awal (§FR-14) -----

    def _build_front_matter(self, doc: Document, blocks: List[DocumentBlock]) -> None:
        front_roles = {
            BlockRole.lembar_pengesahan,
            BlockRole.kata_pengantar,
            BlockRole.abstrak,
            BlockRole.daftar_isi,
            BlockRole.daftar_tabel,
            BlockRole.daftar_gambar,
        }
        rules_tipografi = self.rules.get("tipografi", {})

        for block in blocks:
            if block.role not in front_roles:
                continue
            # Judul bagian
            content = re.sub(r"^#{1,6}\s+", "", block.text_content or block.text_preview)
            if block.role == BlockRole.daftar_isi:
                p = doc.add_paragraph()
                fld = OxmlElement("w:fldSimple")
                fld.set(qn("w:instr"), 'TOC \\o "1-3" \\h \\z \\u')
                p._p.append(fld)
            else:
                p = doc.add_paragraph(content)
                _apply_typography(p, rules_tipografi)

            _add_page_break(doc)

    # ----- Body (§FR-13, FR-15) -----

    def _build_body(self, doc: Document, blocks: List[DocumentBlock]) -> None:
        rules_heading = self.rules.get("heading_bab", {})
        rules_tipografi = self.rules.get("tipografi", {})
        penomoran = rules_heading.get("penomoran", "romawi")

        bab_num = 0
        sub_num = 0
        subsub_num = 0

        for block in blocks:
            if block.role == BlockRole.heading_bab:
                bab_num += 1
                sub_num = 0
                subsub_num = 0
                self._bab_map[block.block_id] = bab_num

                _add_page_break(doc)

                p_title = doc.add_paragraph(block.text_content or block.text_preview)
                _set_heading_style(p_title, 1, rules_heading)

                # Children subbab
                for child in block.children:
                    self._add_subbab(doc, child, bab_num, sub_num, subsub_num, rules_heading, rules_tipografi)

            elif block.role == BlockRole.heading_subbab:
                sub_num += 1
                subsub_num = 0
                p = doc.add_paragraph(block.text_content or block.text_preview)
                _set_heading_style(p, 2, rules_heading)

            elif block.role == BlockRole.paragraf:
                p = doc.add_paragraph((block.text_content or block.text_preview))
                _apply_typography(p, rules_tipografi)

    def _add_subbab(
        self, doc, block, bab_num, sub_num, subsub_num,
        rules_heading, rules_tipografi
    ) -> None:
        p = doc.add_paragraph(block.text_content or block.text_preview)
        _set_heading_style(p, 2, rules_heading)

    # ----- Daftar Pustaka (§FR-16) -----

    def _build_references(self, doc: Document, blocks: List[DocumentBlock]) -> None:
        ref_blocks = [b for b in blocks if b.role == BlockRole.daftar_pustaka]
        if not ref_blocks:
            return
        rules_pustaka = self.rules.get("daftar_pustaka", {})

        _add_page_break(doc)
        for block in ref_blocks:
            p = doc.add_paragraph((block.text_content or block.text_preview))
            pf = p.paragraph_format
            pf.left_indent = Cm(rules_pustaka.get("hanging_indent_cm", 1.25))
            pf.first_line_indent = Cm(-rules_pustaka.get("hanging_indent_cm", 1.25))
            pf.line_spacing = Pt(12 * rules_pustaka.get("spasi_antar", 1))

    # ----- Lampiran (§FR-14) -----

    def _build_appendix(self, doc: Document, blocks: List[DocumentBlock]) -> None:
        lampiran_blocks = [b for b in blocks if b.role == BlockRole.lampiran]
        if not lampiran_blocks:
            return
        rules_lampiran = self.rules.get("lampiran", {})
        label_prefix = rules_lampiran.get("label", "LAMPIRAN")

        for i, block in enumerate(lampiran_blocks, start=1):
            _add_page_break(doc)
            doc.add_paragraph((block.text_content or block.text_preview))
