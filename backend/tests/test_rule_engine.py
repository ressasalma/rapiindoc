"""
tests/test_rule_engine.py
Unit test untuk mesin aturan – tanpa database.
"""

from __future__ import annotations

import pytest
from app.schemas.session import DocType, RuleProfile, RuleSource, StandardMode
from app.services.rule_engine import RuleEngine


@pytest.fixture
def engine():
    return RuleEngine(preset_loader=None)


def test_resolve_all_groups_bawaan(engine):
    """Profil kosong → semua grup pakai aturan bawaan."""
    profile = RuleProfile(doc_type=DocType.makalah)
    resolved, provenance = engine.resolve(profile)

    assert "halaman" in resolved
    assert "tipografi" in resolved
    assert resolved["halaman"]["ukuran_kertas"] == "A4"
    assert provenance["halaman"] == "bawaan"


def test_resolve_manual_override(engine):
    """Override manual harus menang atas semua sumber lain."""
    profile = RuleProfile(
        doc_type=DocType.laporan,
        overrides={"tipografi": {"font": "Arial", "ukuran_pt": 11}},
    )
    resolved, provenance = engine.resolve(profile)

    assert resolved["tipografi"]["font"] == "Arial"
    assert provenance["tipografi"] == "manual"


def test_resolve_bawaan_source(engine):
    """Sumber 'bawaan' untuk bagian tertentu harus menggunakan DEFAULT_RULES."""
    profile = RuleProfile(
        doc_type=DocType.makalah,
        sources={
            "sitasi": RuleSource(**{"from": "bawaan", "style": "APA7"}),
        },
    )
    resolved, provenance = engine.resolve(profile)

    assert resolved["sitasi"]["gaya"] == "APA7"
    assert "bawaan" in provenance["sitasi"]


def test_compatibility_check_error_sitasi_pustaka(engine):
    """Sitasi IEEE + Pustaka APA → Error."""
    profile = RuleProfile(
        doc_type=DocType.laporan,
        overrides={
            "sitasi": {"gaya": "IEEE"},
            "daftar_pustaka": {"gaya": "APA7"},
        },
    )
    resolved, provenance = engine.resolve(profile)
    result = engine.check_compatibility(profile, resolved, provenance)

    assert result.has_errors
    error_groups = [f.group for f in result.findings if f.level.value == "error"]
    assert any("sitasi" in g or "pustaka" in g for g in error_groups)


def test_compatibility_check_ok(engine):
    """Profil konsisten → tidak ada error."""
    profile = RuleProfile(
        doc_type=DocType.makalah,
        overrides={
            "sitasi": {"gaya": "APA7"},
            "daftar_pustaka": {"gaya": "APA7"},
        },
    )
    resolved, provenance = engine.resolve(profile)
    result = engine.check_compatibility(profile, resolved, provenance)

    errors = [f for f in result.findings if f.level.value == "error"]
    # Tidak boleh ada error tentang ketidaksesuaian gaya
    gaya_errors = [e for e in errors if "gaya sitasi" in e.message]
    assert len(gaya_errors) == 0


def test_roman_number_heading(engine):
    """Penomoran romawi default untuk bab."""
    profile = RuleProfile(doc_type=DocType.makalah)
    resolved, _ = engine.resolve(profile)
    assert resolved["heading_bab"]["penomoran"] == "romawi"
