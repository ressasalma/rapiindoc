"""
app/api/routes_presets.py
Endpoint: katalog preset kampus dan aturan (FR-02, FR-22).
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.system import CitationStyle, RuleGroup, RulePreset, University
from app.schemas.preset import (
    CitationStyleOut,
    RuleGroupOut,
    RulePresetOut,
    UniversityOut,
)

router = APIRouter(prefix="/api/v1/presets", tags=["presets"])


# ----- Kampus -----

@router.get("/universities", response_model=List[UniversityOut])
def list_universities(aktif: bool = True, db: Session = Depends(get_db)):
    """Daftar kampus yang tersedia sebagai preset."""
    return db.query(University).filter(University.aktif == aktif).all()


# ----- Grup Aturan (12 bagian) -----

@router.get("/groups", response_model=List[RuleGroupOut])
def list_rule_groups(db: Session = Depends(get_db)):
    """Katalog 12 bagian aturan beserta dependensi (FR-04, FR-06)."""
    return db.query(RuleGroup).order_by(RuleGroup.urutan).all()


# ----- Preset Kampus -----

@router.get("/", response_model=List[RulePresetOut])
def list_presets(
    university_slug: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Daftar preset kampus.
    Filter: university_slug, doc_type.
    Menampilkan versi pedoman dan tanggal verifikasi.
    """
    q = db.query(RulePreset)
    if university_slug:
        q = q.join(University).filter(University.slug == university_slug)
    if doc_type:
        q = q.filter(RulePreset.doc_type == doc_type)
    return q.all()


@router.get("/{preset_id}", response_model=RulePresetOut)
def get_preset(preset_id: int, db: Session = Depends(get_db)):
    """Detail satu preset beserta aturan per bagian (rules_json)."""
    preset = db.query(RulePreset).filter(RulePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset tidak ditemukan.")
    return preset


# ----- Gaya Sitasi -----

@router.get("/citation-styles", response_model=List[CitationStyleOut])
def list_citation_styles(db: Session = Depends(get_db)):
    """Daftar gaya sitasi yang didukung (APA 7, IEEE, Harvard, Chicago)."""
    return db.query(CitationStyle).all()
