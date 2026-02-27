from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Form100AnnotationDto(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    annotation_type: Literal["WOUND_X", "BURN_HATCH", "AMPUTATION", "TOURNIQUET", "NOTE_PIN"]
    x: float
    y: float
    silhouette: Literal["male_front", "male_back", "female_front", "female_back"]
    note: str = ""
    shape_json: dict[str, float] = Field(default_factory=dict)


class Form100DataV2Dto(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    stub: dict[str, Any] = Field(default_factory=dict)
    main: dict[str, Any] = Field(default_factory=dict)
    lesion: dict[str, Any] = Field(default_factory=dict)
    san_loss: dict[str, Any] = Field(default_factory=dict)
    bodymap_gender: Literal["M", "F"] = "M"
    bodymap_annotations: list[Form100AnnotationDto] = Field(default_factory=list)
    bodymap_tissue_types: list[str] = Field(default_factory=list)
    medical_help: dict[str, Any] = Field(default_factory=dict)
    bottom: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class Form100CreateV2Request(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    emr_case_id: int | None = None
    main_full_name: str
    main_unit: str
    main_id_tag: str | None = None
    main_diagnosis: str
    birth_date: date | None = None
    data: Form100DataV2Dto = Field(default_factory=Form100DataV2Dto)


class Form100UpdateV2Request(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    emr_case_id: int | None = None
    main_full_name: str | None = None
    main_unit: str | None = None
    main_id_tag: str | None = None
    main_diagnosis: str | None = None
    birth_date: date | None = None
    data: Form100DataV2Dto | None = None


class Form100SignV2Request(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    signed_by: str | None = None


class Form100V2Filters(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str | None = None
    status: Literal["DRAFT", "SIGNED"] | None = None
    unit: str | None = None
    id_tag: str | None = None
    patient_id: int | None = None
    emr_case_id: int | None = None
    created_from: date | None = None
    created_to: date | None = None


class Form100CardV2ListItemDto(BaseModel):
    id: str
    status: str
    version: int
    main_full_name: str
    birth_date: date | None = None
    main_unit: str | None = None
    main_id_tag: str | None = None
    main_diagnosis: str | None = None
    updated_at: datetime
    is_archived: bool


class Form100CardV2Dto(BaseModel):
    id: str
    legacy_card_id: str | None = None
    emr_case_id: int | None = None
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    status: str
    version: int
    is_archived: bool
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    main_full_name: str
    main_unit: str | None = None
    main_id_tag: str | None = None
    main_diagnosis: str | None = None
    birth_date: date | None = None
    signed_by: str | None = None
    signed_at: datetime | None = None
    data: Form100DataV2Dto = Field(default_factory=Form100DataV2Dto)
