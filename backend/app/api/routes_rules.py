"""
app/api/routes_rules.py
Endpoint: komposisi aturan, pemeriksaan kompatibilitas, pratinjau (FR-05, FR-06, FR-07, FR-08).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.session import CompatibilityResult, RuleProfile
from app.services.rule_engine import RuleEngine

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])

_engine = RuleEngine()


@router.post("/resolve", response_model=dict)
def resolve_rule_profile(profile: RuleProfile):
    """
    Selesaikan Profil Aturan → aturan final per bagian + provenance.
    Dapat dipakai frontend untuk memperbarui pratinjau mini (FR-07).
    """
    resolved, provenance = _engine.resolve(profile)
    return {
        "resolved_rules": resolved,
        "provenance": provenance,
    }


@router.post("/compatibility", response_model=CompatibilityResult)
def check_compatibility(profile: RuleProfile):
    """
    Jalankan pemeriksaan kompatibilitas pada Profil Aturan (FR-06, §5.5).
    Mengembalikan Error/Warning/Info.
    """
    resolved, provenance = _engine.resolve(profile)
    return _engine.check_compatibility(profile, resolved, provenance)


@router.post("/summary")
def get_rule_summary(profile: RuleProfile):
    """
    Ringkasan standar gabungan dalam kalimat per bagian (FR-07).
    """
    resolved, provenance = _engine.resolve(profile)
    summary = []
    for group, source in provenance.items():
        rules = resolved.get(group, {})
        summary.append({
            "group": group,
            "source": source,
            "value_summary": _summarize_group(group, rules),
        })
    return {"summary": summary}


def _summarize_group(group: str, rules: dict) -> str:
    """Buat ringkasan singkat aturan satu bagian."""
    if group == "halaman":
        return (
            f"{rules.get('ukuran_kertas', 'A4')}, "
            f"margin {rules.get('margin_kiri_cm', 4)}-"
            f"{rules.get('margin_atas_cm', 3)}-"
            f"{rules.get('margin_kanan_cm', 3)}-"
            f"{rules.get('margin_bawah_cm', 3)} cm"
        )
    if group == "tipografi":
        return (
            f"{rules.get('font', 'Times New Roman')} "
            f"{rules.get('ukuran_pt', 12)} pt, "
            f"spasi {rules.get('spasi', 1.5)}"
        )
    if group == "sitasi" or group == "daftar_pustaka":
        return rules.get("gaya", "APA7")
    if group == "penomoran_halaman":
        front = rules.get("front", {})
        return f"{front.get('format', 'lower-roman')}, {front.get('posisi', 'bottom-center')}"
    return str(rules)[:80]
