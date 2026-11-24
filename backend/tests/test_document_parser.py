"""
tests/test_document_parser.py
Unit test untuk parser dokumen – parsing teks tempel.
"""

from __future__ import annotations

import pytest
from app.schemas.session import BlockRole
from app.services.document_parser import DocumentParser


@pytest.fixture
def parser():
    return DocumentParser()


SAMPLE_TEXT = """
Laporan Kerja Praktek

IMPLEMENTASI SISTEM INVENTORY BERBASIS WEB

Disusun oleh:
Rani Sari
NIM: 12345678

Dosen Pengampu: Dr. Budi Santoso

Program Studi Teknik Informatika
Fakultas Ilmu Komputer
Universitas Indonesia
Jakarta 2026

BAB I
PENDAHULUAN

1.1 Latar Belakang
Sistem inventory manual memiliki banyak kelemahan yang berdampak pada efisiensi operasional perusahaan.

1.2 Rumusan Masalah
Bagaimana merancang sistem inventory berbasis web yang efisien?

BAB II
TINJAUAN PUSTAKA

Tinjauan pustaka membahas teori dasar yang digunakan dalam penelitian ini.

DAFTAR PUSTAKA

Santoso, B. (2026). Sistem Informasi. Jakarta: Penerbit UI.
"""


def test_parse_text_basic(parser):
    blocks, cover_data, raw_texts = parser.parse_text(SAMPLE_TEXT)
    assert len(blocks) > 0
    assert len(raw_texts) > 0


def test_detects_heading_bab(parser):
    blocks, _, _ = parser.parse_text(SAMPLE_TEXT)
    roles = [b.role for b in blocks]
    assert BlockRole.heading_bab in roles


def test_detects_daftar_pustaka(parser):
    blocks, _, _ = parser.parse_text(SAMPLE_TEXT)
    roles = [b.role for b in blocks]
    assert BlockRole.daftar_pustaka in roles


def test_extracts_cover_data(parser):
    blocks, cover_data, _ = parser.parse_text(SAMPLE_TEXT)
    assert cover_data.nim == "12345678"


def test_confidence_range(parser):
    blocks, _, _ = parser.parse_text(SAMPLE_TEXT)
    for block in blocks:
        assert 0.0 <= block.confidence <= 1.0, (
            f"Confidence out of range for block {block.block_id}: {block.confidence}"
        )


def test_ambiguous_flag(parser):
    """Blok dengan confidence < 0.6 harus is_ambiguous=True."""
    blocks, _, _ = parser.parse_text(SAMPLE_TEXT)
    for block in blocks:
        if block.confidence < 0.6:
            assert block.is_ambiguous, f"Block {block.block_id} seharusnya is_ambiguous"


def test_subbab_detection(parser):
    blocks, _, _ = parser.parse_text(SAMPLE_TEXT)
    roles = [b.role for b in blocks]
    assert BlockRole.heading_subbab in roles
