from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

FORM100_V2_STATUS_DRAFT = "DRAFT"
FORM100_V2_STATUS_SIGNED = "SIGNED"

BODYMAP_SILHOUETTES = {"male_front", "male_back", "female_front", "female_back"}
BODYMAP_ANNOTATION_TYPES = {"WOUND_X", "BURN_HATCH", "AMPUTATION", "TOURNIQUET", "NOTE_PIN"}


@dataclass(slots=True)
class AnnotationData:
    annotation_type: str
    x: float
    y: float
    silhouette: str
    note: str = ""


@dataclass(slots=True)
class Form100DataV2:
    stub: dict[str, Any] = field(default_factory=dict)
    main: dict[str, Any] = field(default_factory=dict)
    lesion: dict[str, Any] = field(default_factory=dict)
    san_loss: dict[str, Any] = field(default_factory=dict)
    bodymap_gender: str = "M"
    bodymap_annotations: list[AnnotationData] = field(default_factory=list)
    bodymap_tissue_types: list[str] = field(default_factory=list)
    medical_help: dict[str, Any] = field(default_factory=dict)
    bottom: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Form100CardV2:
    id: str
    status: str
    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    is_archived: bool
    main_full_name: str
    main_unit: str | None
    main_id_tag: str | None
    main_diagnosis: str | None
    birth_date: date | None = None
    signed_by: str | None = None
    signed_at: datetime | None = None
    legacy_card_id: str | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    emr_case_id: int | None = None
    data: Form100DataV2 = field(default_factory=Form100DataV2)
