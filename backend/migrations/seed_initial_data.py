"""
migrations/seed_initial_data.py
Seed data sistem awal ke MySQL:
- Grup aturan (12 bagian)
- Kampus contoh
- Preset bawaan (default umum akademik Indonesia)
- Gaya sitasi
- Kamus kata kunci

Jalankan: python migrations/seed_initial_data.py
"""

from __future__ import annotations

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime

from app.db.database import Base, engine, SessionLocal
from app.models.system import (
    CitationStyle,
    KeywordDictionary,
    RuleGroup,
    RulePreset,
    RulePresetGroup,
    University,
)

# ============================================================
# Skema
# ============================================================

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("[OK] Tabel dibuat.")


# ============================================================
# Data Seed
# ============================================================

RULE_GROUPS = [
    {"key": "halaman",           "nama": "Halaman dan Margin",        "urutan": 1,  "depends_on": None,                     "bundle_key": None},
    {"key": "tipografi",         "nama": "Tipografi Isi",             "urutan": 2,  "depends_on": "heading_bab",             "bundle_key": None},
    {"key": "cover",             "nama": "Cover",                     "urutan": 3,  "depends_on": "bagian_awal",             "bundle_key": None},
    {"key": "bagian_awal",       "nama": "Bagian Awal",               "urutan": 4,  "depends_on": None,                     "bundle_key": None},
    {"key": "heading_bab",       "nama": "Heading Bab dan Subbab",    "urutan": 5,  "depends_on": None,                     "bundle_key": None},
    {"key": "penomoran_halaman", "nama": "Penomoran Halaman",         "urutan": 6,  "depends_on": "bagian_awal,cover",      "bundle_key": None},
    {"key": "daftar_isi",        "nama": "Daftar Isi/Tabel/Gambar",   "urutan": 7,  "depends_on": "heading_bab",             "bundle_key": None},
    {"key": "tabel_gambar",      "nama": "Tabel, Gambar, Persamaan",  "urutan": 8,  "depends_on": "heading_bab,halaman",    "bundle_key": None},
    {"key": "sitasi",            "nama": "Kutipan dan Sitasi",        "urutan": 9,  "depends_on": "daftar_pustaka",          "bundle_key": "pustaka_bundle"},
    {"key": "daftar_pustaka",    "nama": "Daftar Pustaka",            "urutan": 10, "depends_on": "sitasi",                 "bundle_key": "pustaka_bundle"},
    {"key": "lampiran",          "nama": "Lampiran",                  "urutan": 11, "depends_on": None,                     "bundle_key": None},
    {"key": "header_footer",     "nama": "Header dan Footer",         "urutan": 12, "depends_on": None,                     "bundle_key": None},
]


DEFAULT_RULES_PER_GROUP = {
    "halaman": {
        "ukuran_kertas": "A4",
        "margin_kiri_cm": 4.0,
        "margin_atas_cm": 3.0,
        "margin_kanan_cm": 3.0,
        "margin_bawah_cm": 3.0,
    },
    "tipografi": {
        "font": "Times New Roman",
        "ukuran_pt": 12,
        "spasi": 1.5,
        "justify": True,
        "indentasi_pertama_cm": 1.25,
    },
    "cover": {
        "urutan": ["jenis_dokumen", "judul", "logo", "nama_nim", "dosen", "prodi", "fakultas", "institusi", "kota_tahun"],
        "judul_kapital": True,
        "judul_tebal": True,
        "judul_tengah": True,
        "tanpa_nomor_halaman": True,
    },
    "bagian_awal": {
        "judul_tengah": True,
        "judul_tebal": True,
        "judul_kapital": True,
        "abstrak_min_kata": 150,
        "abstrak_max_kata": 250,
        "abstrak_spasi": 1,
        "kata_kunci_min": 3,
        "kata_kunci_max": 5,
        "kata_kunci_miring": True,
    },
    "heading_bab": {
        "h1_format": "BAB {nomor}",
        "h1_kapital": True,
        "h1_tebal": True,
        "h1_tengah": True,
        "h1_ukuran_pt": 14,
        "h1_halaman_baru": True,
        "h2_format": "{bab}.{sub}",
        "h2_tebal": True,
        "h3_format": "{bab}.{sub}.{subsub}",
        "h3_tebal": True,
        "h3_miring": True,
        "penomoran": "romawi",
    },
    "penomoran_halaman": {
        "cover": "hidden_counted_as_i",
        "front": {"format": "lower-roman", "posisi": "bottom-center"},
        "main": {
            "format": "arabic",
            "mulai_dari": "BAB I",
            "halaman_bab": "bottom-center",
            "halaman_lain": "top-right",
        },
        "appendix": {"format": "arabic", "lanjutkan": True},
    },
    "daftar_isi": {
        "level": 3,
        "leader_dots": True,
        "nomor_kanan": True,
        "sertakan_bagian_awal": True,
    },
    "tabel_gambar": {
        "caption_tabel_posisi": "atas",
        "caption_gambar_posisi": "bawah",
        "format_nomor": "bab.urut",
        "teks_tabel_pt": 10,
        "header_ulang": True,
        "sumber_di_bawah": True,
    },
    "sitasi": {
        "gaya": "APA7",
        "batas_kutipan_blok": 40,
        "indentasi_blok_cm": 1.25,
    },
    "daftar_pustaka": {
        "gaya": "APA7",
        "urutan": "abjad",
        "hanging_indent_cm": 1.25,
        "spasi_antar": 1,
        "doi_hyperlink": True,
    },
    "lampiran": {
        "label": "LAMPIRAN",
        "penomoran": "arab",
        "halaman_baru": True,
        "di_daftar_isi": True,
        "penomoran_halaman_lanjut": True,
    },
    "header_footer": {
        "footer_nomor_halaman": True,
        "header_aktif": False,
        "header_isi": "judul_pendek",
        "garis_pemisah": False,
    },
}


UNIVERSITIES = [
    {"nama": "Universitas Indonesia", "slug": "ui"},
    {"nama": "Institut Teknologi Bandung", "slug": "itb"},
    {"nama": "Universitas Gadjah Mada", "slug": "ugm"},
    {"nama": "Institut Teknologi Sepuluh Nopember", "slug": "its"},
    {"nama": "Universitas Brawijaya", "slug": "ub"},
]


CITATION_STYLES = [
    {
        "nama": "APA7",
        "config_json": {
            "nama_lengkap": "APA 7th Edition",
            "urutan": "abjad",
            "pola_sitasi": "(Penulis, Tahun)",
            "pola_pustaka": "Penulis, A. A. (Tahun). Judul. Penerbit.",
        },
    },
    {
        "nama": "IEEE",
        "config_json": {
            "nama_lengkap": "IEEE Reference Style",
            "urutan": "kemunculan",
            "pola_sitasi": "[n]",
            "pola_pustaka": "[n] A. Penulis, \"Judul,\" Jurnal, vol. x, pp. x–x, Tahun.",
        },
    },
    {
        "nama": "Harvard",
        "config_json": {
            "nama_lengkap": "Harvard Referencing",
            "urutan": "abjad",
            "pola_sitasi": "(Penulis Tahun)",
            "pola_pustaka": "Penulis, A. A. Tahun. Judul. Tempat: Penerbit.",
        },
    },
    {
        "nama": "Chicago",
        "config_json": {
            "nama_lengkap": "Chicago 17th Edition",
            "urutan": "abjad",
            "pola_sitasi": "(Penulis Tahun)",
            "pola_pustaka": "Penulis, Nama. Tahun. Judul. Tempat: Penerbit.",
        },
    },
    {
        "nama": "MLA",
        "config_json": {
            "nama_lengkap": "MLA 9th Edition",
            "urutan": "abjad",
            "pola_sitasi": "(Penulis halaman)",
            "pola_pustaka": "Penulis. Judul. Penerbit, Tahun.",
        },
    },
]


GENERAL_PRESETS = [
    {
        "slug": "akademik-umum-indonesia",
        "nama": "Standar Akademik Umum Indonesia",
        "versi": "2026-1",
        "sumber": "Kompilasi praktik umum pedoman penulisan perguruan tinggi Indonesia; wajib disesuaikan dengan institusi tujuan.",
        "overrides": {},
    },
    {
        "slug": "apa-7",
        "nama": "APA 7th Edition",
        "versi": "7",
        "sumber": "Publication Manual of the American Psychological Association, 7th edition.",
        "overrides": {
            "halaman": {"ukuran_kertas": "A4", "margin_kiri_cm": 2.54, "margin_atas_cm": 2.54, "margin_kanan_cm": 2.54, "margin_bawah_cm": 2.54},
            "tipografi": {"font": "Times New Roman", "ukuran_pt": 12, "spasi": 2, "justify": False, "indentasi_pertama_cm": 1.27},
            "sitasi": {"gaya": "APA7"},
            "daftar_pustaka": {"gaya": "APA7", "urutan": "abjad", "hanging_indent_cm": 1.27, "spasi_antar": 2},
        },
    },
    {
        "slug": "ieee",
        "nama": "IEEE",
        "versi": "2025",
        "sumber": "IEEE Editorial Style Manual dan IEEE Author Center; template publikasi tujuan tetap menjadi acuan akhir.",
        "overrides": {
            "halaman": {"ukuran_kertas": "A4", "margin_kiri_cm": 1.9, "margin_atas_cm": 1.9, "margin_kanan_cm": 1.9, "margin_bawah_cm": 2.54},
            "tipografi": {"font": "Times New Roman", "ukuran_pt": 10, "spasi": 1, "justify": True, "indentasi_pertama_cm": 0},
            "sitasi": {"gaya": "IEEE"},
            "daftar_pustaka": {"gaya": "IEEE", "urutan": "kemunculan", "hanging_indent_cm": 0, "spasi_antar": 1},
        },
    },
    {
        "slug": "mla-9",
        "nama": "MLA 9th Edition",
        "versi": "9",
        "sumber": "MLA Handbook, 9th edition, Modern Language Association.",
        "overrides": {
            "halaman": {"ukuran_kertas": "A4", "margin_kiri_cm": 2.54, "margin_atas_cm": 2.54, "margin_kanan_cm": 2.54, "margin_bawah_cm": 2.54},
            "tipografi": {"font": "Times New Roman", "ukuran_pt": 12, "spasi": 2, "justify": False, "indentasi_pertama_cm": 1.27},
            "sitasi": {"gaya": "MLA"},
            "daftar_pustaka": {"gaya": "MLA", "urutan": "abjad", "hanging_indent_cm": 1.27, "spasi_antar": 2},
        },
    },
    {
        "slug": "chicago-17",
        "nama": "Chicago 17th Edition",
        "versi": "17",
        "sumber": "The Chicago Manual of Style, 17th edition, University of Chicago Press.",
        "overrides": {
            "halaman": {"ukuran_kertas": "A4", "margin_kiri_cm": 2.54, "margin_atas_cm": 2.54, "margin_kanan_cm": 2.54, "margin_bawah_cm": 2.54},
            "tipografi": {"font": "Times New Roman", "ukuran_pt": 12, "spasi": 2, "justify": False, "indentasi_pertama_cm": 1.27},
            "sitasi": {"gaya": "Chicago"},
            "daftar_pustaka": {"gaya": "Chicago", "urutan": "abjad", "hanging_indent_cm": 1.27, "spasi_antar": 2},
        },
    },
]


KEYWORD_DICTIONARY = [
    # Makalah
    {"doc_type": "makalah", "peran": "heading_bab", "kata_kunci": "pendahuluan", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_subbab", "kata_kunci": "latar belakang", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_subbab", "kata_kunci": "rumusan masalah", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_subbab", "kata_kunci": "tujuan", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_bab", "kata_kunci": "pembahasan", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_bab", "kata_kunci": "penutup", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_subbab", "kata_kunci": "kesimpulan", "bahasa": "id"},
    {"doc_type": "makalah", "peran": "heading_subbab", "kata_kunci": "saran", "bahasa": "id"},
    # Laporan
    {"doc_type": "laporan", "peran": "heading_bab", "kata_kunci": "tinjauan pustaka", "bahasa": "id"},
    {"doc_type": "laporan", "peran": "heading_bab", "kata_kunci": "landasan teori", "bahasa": "id"},
    {"doc_type": "laporan", "peran": "heading_bab", "kata_kunci": "metodologi", "bahasa": "id"},
    {"doc_type": "laporan", "peran": "heading_bab", "kata_kunci": "pelaksanaan", "bahasa": "id"},
    {"doc_type": "laporan", "peran": "heading_bab", "kata_kunci": "hasil dan pembahasan", "bahasa": "id"},
    # Proposal
    {"doc_type": "proposal", "peran": "heading_bab", "kata_kunci": "deskripsi kegiatan", "bahasa": "id"},
    {"doc_type": "proposal", "peran": "heading_bab", "kata_kunci": "rencana pelaksanaan", "bahasa": "id"},
    {"doc_type": "proposal", "peran": "heading_subbab", "kata_kunci": "jadwal", "bahasa": "id"},
    {"doc_type": "proposal", "peran": "heading_subbab", "kata_kunci": "anggaran", "bahasa": "id"},
    # Jurnal
    {"doc_type": "jurnal", "peran": "abstrak", "kata_kunci": "abstract", "bahasa": "en"},
    {"doc_type": "jurnal", "peran": "heading_bab", "kata_kunci": "metode", "bahasa": "id"},
    {"doc_type": "jurnal", "peran": "heading_bab", "kata_kunci": "results", "bahasa": "en"},
    # Umum
    {"doc_type": "*", "peran": "daftar_pustaka", "kata_kunci": "daftar pustaka", "bahasa": "id"},
    {"doc_type": "*", "peran": "daftar_pustaka", "kata_kunci": "referensi", "bahasa": "id"},
    {"doc_type": "*", "peran": "daftar_pustaka", "kata_kunci": "bibliography", "bahasa": "en"},
]


# ============================================================
# Runner
# ============================================================

def seed_json_presets(db):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "presets_aturan_format.json"))
    with open(path, encoding="utf-8") as file:
        payload = json.load(file)

    universities = {university.slug: university for university in db.query(University).all()}
    campus_slugs = {
        "ui": "ui",
        "itb": "itb",
        "ugm": "ugm",
        "ipb": "ipb",
        "its": "its",
    }
    inserted = 0
    for item in payload.get("presets", []):
        university_id = None
        if item.get("tipe") == "kampus":
            source = item.get("sumber", {})
            title = source.get("judul", item.get("nama", "")) if isinstance(source, dict) else item.get("nama", "")
            slug = next((value for key, value in campus_slugs.items() if key.upper() in title.upper()), None)
            if slug and slug not in universities:
                university = University(nama=title.split(" - ")[0], slug=slug, aktif=True)
                db.add(university)
                db.flush()
                universities[slug] = university
            university_id = universities.get(slug).id if slug and slug in universities else None

        source = item.get("sumber", {})
        source_text = source.get("url", "") if isinstance(source, dict) else str(source or "")
        source_text = f"{item.get('status_verifikasi', '')}. {source_text}".strip()
        for doc_type in item.get("jenis_dokumen", []):
            preset = RulePreset(
                university_id=university_id,
                doc_type=doc_type,
                versi=payload.get("_meta", {}).get("versi_skema", "1.0"),
                sumber_pedoman=source_text or item.get("nama", "Preset JSON"),
                diverifikasi_pada=datetime.now(),
            )
            db.add(preset)
            db.flush()
            for group_key, rules in item.get("groups", {}).items():
                rules = dict(rules)
                diatur = bool(rules.pop("diatur", True))
                db.add(RulePresetGroup(preset_id=preset.id, group_key=group_key, rules_json=rules, diatur=diatur))
            inserted += 1
    db.commit()
    print(f"[OK] {inserted} preset JSON dan grup aturan dimasukkan.")


def seed():
    create_tables()

    with SessionLocal() as db:
        # Bersihkan data lama
        db.query(KeywordDictionary).delete()
        db.query(RulePresetGroup).delete()
        db.query(RulePreset).delete()
        db.query(RuleGroup).delete()
        db.query(CitationStyle).delete()
        db.query(University).delete()
        db.commit()

        # Grup aturan
        for g in RULE_GROUPS:
            db.add(RuleGroup(**g))
        db.commit()
        print(f"[OK] {len(RULE_GROUPS)} rule groups.")

        # Kampus
        for u in UNIVERSITIES:
            db.add(University(**u))
        db.commit()
        print(f"[OK] {len(UNIVERSITIES)} universities.")

        # Preset bawaan (tanpa university_id) untuk setiap jenis dokumen
        doc_types = ["makalah", "laporan", "proposal", "jurnal"]
        for dt in doc_types:
            preset = RulePreset(
                university_id=None,
                doc_type=dt,
                versi="2026-1",
                sumber_pedoman="Standar bawaan umum akademik Indonesia (RapiInDoc v1.2)",
                diverifikasi_pada=datetime(2026, 11, 21),
            )
            db.add(preset)
            db.flush()

            for group_key, rules in DEFAULT_RULES_PER_GROUP.items():
                db.add(RulePresetGroup(
                    preset_id=preset.id,
                    group_key=group_key,
                    rules_json=rules,
                    diatur=True,
                ))
        db.commit()
        for general in GENERAL_PRESETS:
            for dt in doc_types:
                preset = RulePreset(
                    university_id=None,
                    doc_type=dt,
                    versi=general["versi"],
                    sumber_pedoman=general["sumber"],
                    diverifikasi_pada=datetime(2026, 11, 21),
                )
                db.add(preset)
                db.flush()
                for group_key, base_rules in DEFAULT_RULES_PER_GROUP.items():
                    rules = dict(base_rules)
                    rules.update(general["overrides"].get(group_key, {}))
                    db.add(RulePresetGroup(preset_id=preset.id, group_key=group_key, rules_json=rules, diatur=True))
        db.commit()
        print(f"[OK] {len(doc_types) * (1 + len(GENERAL_PRESETS))} presets bawaan.")

        # Gaya sitasi
        for cs in CITATION_STYLES:
            db.add(CitationStyle(**cs))
        db.commit()
        print(f"[OK] {len(CITATION_STYLES)} citation styles.")

        # Kamus kata kunci
        for kw in KEYWORD_DICTIONARY:
            db.add(KeywordDictionary(**kw))
        db.commit()
        print(f"[OK] {len(KEYWORD_DICTIONARY)} keywords.")
        seed_json_presets(db)

    print("\n[OK] Seed selesai.")


if __name__ == "__main__":
    seed()
