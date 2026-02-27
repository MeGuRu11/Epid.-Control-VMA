from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AnnotationData:
    """Single body-map annotation placed by the physician."""
    annotation_type: str   # 'WOUND_X' | 'BURN_HATCH' | 'AMPUTATION' | 'TOURNIQUET' | 'NOTE_PIN'
    x: float               # normalised 0.0–1.0 within the silhouette bounding rect
    y: float
    silhouette: str        # 'male_front' | 'male_back' | 'female_front' | 'female_back'
    note: str = ""         # text note (NOTE_PIN only)


@dataclass
class Form100Data:
    # ── Корешок ─────────────────────────────────────────────────────────────
    stub_issued_time: Optional[str] = None
    stub_issued_date: Optional[str] = None
    stub_rank: Optional[str] = None
    stub_unit: Optional[str] = None
    stub_full_name: Optional[str] = None
    stub_id_tag: Optional[str] = None
    stub_injury_time: Optional[str] = None
    stub_injury_date: Optional[str] = None
    stub_evacuation_method: Optional[str] = None   # 'airplane'|'ambu'|'truck'
    stub_evacuation_dest: Optional[str] = None     # 'lying'|'sitting'|'stretcher'
    stub_med_help: list[str] = field(default_factory=list)
    stub_antibiotic_dose: Optional[str] = None
    stub_pss_pgs_dose: Optional[str] = None
    stub_toxoid_type: Optional[str] = None
    stub_antidote_type: Optional[str] = None
    stub_analgesic_dose: Optional[str] = None
    stub_transfusion: bool = False
    stub_immobilization: bool = False
    stub_tourniquet: bool = False
    stub_diagnosis: Optional[str] = None

    # ── Основной бланк — идентификация ──────────────────────────────────────
    main_issued_place: Optional[str] = None
    main_issued_time: Optional[str] = None
    main_issued_date: Optional[str] = None
    main_rank: Optional[str] = None
    main_unit: Optional[str] = None
    main_full_name: Optional[str] = None
    main_id_tag: Optional[str] = None
    main_injury_time: Optional[str] = None
    main_injury_date: Optional[str] = None

    # ── Вид поражения ────────────────────────────────────────────────────────
    lesion_types: list[str] = field(default_factory=list)
    san_loss_types: list[str] = field(default_factory=list)
    isolation_required: bool = False

    # ── Bodymap ──────────────────────────────────────────────────────────────
    bodymap_gender: str = "M"          # 'M' | 'F'
    bodymap_annotations: list[AnnotationData] = field(default_factory=list)
    bodymap_tissue_types: list[str] = field(default_factory=list)

    # ── Медицинская помощь ───────────────────────────────────────────────────
    mp_antibiotic: bool = False
    mp_antibiotic_dose: Optional[str] = None
    mp_serum_pss: bool = False
    mp_serum_pgs: bool = False
    mp_serum_dose: Optional[str] = None
    mp_toxoid: Optional[str] = None
    mp_antidote: Optional[str] = None
    mp_analgesic: bool = False
    mp_analgesic_dose: Optional[str] = None
    mp_transfusion_blood: bool = False
    mp_transfusion_substitute: bool = False
    mp_immobilization: bool = False
    mp_bandage: bool = False

    # ── Нижний блок ──────────────────────────────────────────────────────────
    tourniquet_time: Optional[str] = None
    sanitation_type: Optional[str] = None   # 'full'|'partial'|'none'
    evacuation_dest: Optional[str] = None   # 'lying'|'sitting'|'stretcher'
    evacuation_priority: Optional[str] = None  # 'I'|'II'|'III'
    transport_type: Optional[str] = None    # 'car'|'ambu'|'ship'|'heli'|'plane'
    doctor_signature: Optional[str] = None
    main_diagnosis: Optional[str] = None

    # ── Флаги ────────────────────────────────────────────────────────────────
    flag_emergency: bool = False
    flag_radiation: bool = False
    flag_sanitation: bool = False


@dataclass
class Form100:
    """Aggregate root for Форма 100 МО РФ."""
    id: Optional[int]
    emr_case_id: int
    created_at: datetime
    created_by: Optional[int]
    is_archived: bool
    data: Form100Data
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    artifact_path: Optional[str] = None
    artifact_sha256: Optional[str] = None
