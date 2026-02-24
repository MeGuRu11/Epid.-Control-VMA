from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LabSampleCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    patient_id: int
    emr_case_id: int | None = None
    material_type_id: int
    material_location: str | None = None
    medium: str | None = None
    study_kind: str | None = Field(default="primary", pattern="^(primary|repeat)$")
    ordered_at: datetime | None = None
    taken_at: datetime | None = None
    delivered_at: datetime | None = None
    created_by: int | None = None


class LabSampleResultUpdate(BaseModel):
    growth_result_at: datetime | None = None
    growth_flag: int | None = Field(default=None)
    colony_desc: str | None = None
    microscopy: str | None = None
    cfu: str | None = None
    qc_status: str | None = Field(default=None, pattern="^(valid|conditional|rejected)$")
    microorganism_id: int | None = None
    microorganism_free: str | None = None

    susceptibility: list[dict] = Field(default_factory=list)  # each dict: antibiotic_id, ris, mic_mg_l, method, group_id?
    phages: list[dict] = Field(default_factory=list)  # each dict: phage_id/free, diameter


class LabSampleUpdateRequest(BaseModel):
    material_type_id: int | None = None
    material_location: str | None = None
    medium: str | None = None
    study_kind: str | None = Field(default=None, pattern="^(primary|repeat)$")
    ordered_at: datetime | None = None
    taken_at: datetime | None = None
    delivered_at: datetime | None = None


class LabSampleResponse(BaseModel):
    id: int
    lab_no: str
    material_type_id: int
    material_location: str | None = None
    medium: str | None = None
    taken_at: datetime | None
    growth_flag: int | None
    qc_due_at: datetime | None = None
    qc_status: str | None = None
    microorganism_id: int | None = None
    microorganism_free: str | None = None
