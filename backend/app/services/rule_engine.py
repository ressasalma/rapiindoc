"""
app/services/rule_engine.py
Mesin komposisi dan resolusi aturan (PRD §5).

Urutan resolusi per bagian (§5.2):
  1. Edit manual pengguna
  2. Sumber yang dipilih untuk bagian itu
  3. Standar dasar yang dipilih
  4. Standar bawaan jenis dokumen

Mesin ini DETERMINISTIK: input dan aturan sama → hasil sama.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.schemas.session import (
    CompatibilityFinding,
    CompatibilityResult,
    FindingLevel,
    RuleProfile,
    RuleSource,
)


# ----- Aturan Bawaan per Jenis Dokumen -----

DEFAULT_RULES: Dict[str, Dict[str, Any]] = {
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
        "h2_kiri": True,
        "h3_format": "{bab}.{sub}.{subsub}",
        "h3_tebal": True,
        "h3_miring": True,
        "penomoran": "romawi",   # romawi | arab | huruf
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
        "format_nomor": "bab.urut",   # mis. Tabel 2.1
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


# Aturan yang terhubung (bundle) – PRD §5.4
BUNDLES: Dict[str, str] = {
    "sitasi": "daftar_pustaka",
    "daftar_pustaka": "sitasi",
}

# Dependensi antar bagian
DEPENDENCIES: Dict[str, List[str]] = {
    "daftar_isi": ["heading_bab"],
    "penomoran_halaman": ["bagian_awal", "cover"],
    "tabel_gambar": ["heading_bab", "halaman"],
    "cover": ["bagian_awal"],
    "tipografi": ["heading_bab"],
}


class RuleEngine:
    """
    Mesin komposisi aturan – menggabungkan sumber berbeda
    menjadi Profil Aturan final dengan provenance per bagian.
    """

    def __init__(self, preset_loader=None):
        """
        preset_loader: callable(preset_slug, doc_type) -> Dict[group_key, rules_dict]
        Jika None, hanya pakai aturan bawaan.
        """
        self._loader = preset_loader

    def resolve(self, profile: RuleProfile) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Selesaikan Profil Aturan → (resolved_rules, provenance).
        resolved_rules: group_key -> dict aturan final
        provenance: group_key -> label sumber
        """
        enabled_groups = profile.groups.get("enabled") if profile.groups else None
        all_groups = enabled_groups or list(DEFAULT_RULES.keys())
        resolved: Dict[str, Any] = {}
        provenance: Dict[str, str] = {}

        # Muat preset dasar dari DB (bila ada)
        base_rules: Dict[str, Any] = {}
        if profile.base and self._loader:
            base_preset = profile.base.get("preset")
            if base_preset:
                base_rules = self._loader(base_preset, profile.doc_type) or {}

        for group in all_groups:
            rules, source_label = self._resolve_group(
                group, profile, base_rules
            )
            resolved[group] = rules
            provenance[group] = source_label

        return resolved, provenance

    def _resolve_group(
        self,
        group: str,
        profile: RuleProfile,
        base_rules: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], str]:
        """Resolusi satu bagian dengan urutan §5.2."""

        # 1. Override manual
        if group in profile.overrides:
            return {**DEFAULT_RULES.get(group, {}), **profile.overrides[group]}, "manual"

        # 2. Sumber spesifik yang dipilih untuk bagian ini
        if group in profile.sources:
            src: RuleSource = profile.sources[group]
            rules = self._load_source(src, group, profile.doc_type)
            if rules is not None:
                label = self._source_label(src)
                return rules, label
            # Sumber tidak mengatur bagian ini → turun ke langkah 3

        # 3. Standar dasar
        if group in base_rules and base_rules[group]:
            return base_rules[group], f"dasar ({profile.base.get('preset', 'bawaan') if profile.base else 'bawaan'})"

        # 4. Bawaan
        return DEFAULT_RULES.get(group, {}), "bawaan"

    def _load_source(
        self, src: RuleSource, group: str, doc_type: str
    ) -> Optional[Dict[str, Any]]:
        from_field = src.from_
        if from_field == "bawaan":
            return DEFAULT_RULES.get(group)
        if from_field == "manual":
            return None  # manual sudah ditangani di overrides
        if from_field == "preset" and self._loader and src.preset:
            loaded = self._loader(src.preset, doc_type) or {}
            return loaded.get(group)
        if from_field == "acuan":
            # Aturan dari dokumen acuan sudah ada di profile.sources[group]
            # sebagai dict extra (confidence disimpan di RuleSource)
            return None
        return None

    @staticmethod
    def _source_label(src: RuleSource) -> str:
        from_field = src.from_
        if from_field == "bawaan":
            return f"bawaan ({src.style or ''})"
        if from_field == "preset":
            return src.preset or "preset"
        if from_field == "acuan":
            conf = f" ({src.confidence:.0%})" if src.confidence else ""
            return f"acuan{conf}"
        if from_field == "manual":
            return "manual"
        return from_field

    # ----- Pemeriksaan Kompatibilitas (§5.5) -----

    def check_compatibility(
        self, profile: RuleProfile, resolved_rules: Dict[str, Any], provenance: Dict[str, str]
    ) -> CompatibilityResult:
        findings: List[CompatibilityFinding] = []

        # Error: Sitasi IEEE tapi pustaka APA (atau sebaliknya)
        sitasi_gaya = resolved_rules.get("sitasi", {}).get("gaya", "")
        pustaka_gaya = resolved_rules.get("daftar_pustaka", {}).get("gaya", "")
        if sitasi_gaya and pustaka_gaya and sitasi_gaya != pustaka_gaya:
            findings.append(CompatibilityFinding(
                level=FindingLevel.error,
                group="sitasi/daftar_pustaka",
                message=(
                    f"Gaya sitasi ({sitasi_gaya}) dan daftar pustaka ({pustaka_gaya}) berbeda. "
                    "Selaraskan keduanya atau konfirmasi secara sadar."
                ),
            ))

        # Warning: gaya penomoran heading dan daftar isi berbeda
        heading_penomoran = resolved_rules.get("heading_bab", {}).get("penomoran", "")
        daftar_isi_level = resolved_rules.get("daftar_isi", {}).get("level", 3)
        if provenance.get("heading_bab") != provenance.get("daftar_isi"):
            findings.append(CompatibilityFinding(
                level=FindingLevel.warning,
                group="daftar_isi",
                message=(
                    "Sumber heading bab dan daftar isi berbeda; "
                    "pastikan level dan gaya penomoran konsisten."
                ),
            ))

        # Warning: Sitasi dan pustaka dari sumber berbeda (tautan dilepas)
        src_sitasi = provenance.get("sitasi", "")
        src_pustaka = provenance.get("daftar_pustaka", "")
        if src_sitasi != src_pustaka:
            findings.append(CompatibilityFinding(
                level=FindingLevel.warning,
                group="sitasi/daftar_pustaka",
                message=(
                    f"Sitasi ({src_sitasi}) dan daftar pustaka ({src_pustaka}) "
                    "dari sumber berbeda. Periksa konsistensi gaya."
                ),
            ))

        # Info: bagian yang tidak diatur
        for group in DEFAULT_RULES:
            if group in profile.sources:
                src = profile.sources[group]
                loaded = self._load_source(src, group, profile.doc_type)
                if loaded is None and src.from_ not in ("bawaan", "manual"):
                    findings.append(CompatibilityFinding(
                        level=FindingLevel.info,
                        group=group,
                        message=f"Sumber tidak mengatur bagian '{group}'; memakai cadangan.",
                    ))

        return CompatibilityResult(
            findings=findings,
            has_errors=any(f.level == FindingLevel.error for f in findings),
            has_warnings=any(f.level == FindingLevel.warning for f in findings),
        )
