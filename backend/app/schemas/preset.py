"""
app/schemas/preset.py
Pydantic schemas untuk preset kampus dan aturan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UniversityOut(BaseModel):
    id: int
    nama: str
    slug: str
    aktif: bool

    model_config = {"from_attributes": True}


class RuleGroupOut(BaseModel):
    key: str
    nama: str
    urutan: int
    depends_on: Optional[str]
    bundle_key: Optional[str]

    model_config = {"from_attributes": True}


class RulePresetGroupOut(BaseModel):
    group_key: str
    rules_json: Dict[str, Any]
    diatur: bool

    model_config = {"from_attributes": True}


class RulePresetOut(BaseModel):
    id: int
    university_id: Optional[int]
    doc_type: str
    jenjang_fakultas: Optional[str]
    versi: str
    sumber_pedoman: Optional[str]
    diverifikasi_pada: Optional[datetime]
    groups: List[RulePresetGroupOut] = []

    model_config = {"from_attributes": True}


class CitationStyleOut(BaseModel):
    id: int
    nama: str
    config_json: Dict[str, Any]

    model_config = {"from_attributes": True}
