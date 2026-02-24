from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Form100MarkDto(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    side: str
    type: str
    shape_json: dict[str, Any] = Field(default_factory=dict)
    meta_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    created_by: str | None = None


class Form100StageCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    stage_name: str = Field(..., min_length=1)
    received_at: datetime | None = None
    updated_diagnosis_text: str | None = None
    updated_diagnosis_code: str | None = None
    procedures_text: str | None = None
    evac_next_destination: str | None = None
    evac_next_dt: datetime | None = None
    condition_at_transfer: str | None = None
    outcome: str | None = None
    outcome_date: date | None = None
    burial_place: str | None = None
    signed_by: str | None = None
    signed_at: datetime | None = None


class Form100StageDto(Form100StageCreateRequest):
    id: str
    card_id: str


class Form100CreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    last_name: str
    first_name: str
    middle_name: str | None = None
    birth_date: date
    rank: str
    unit: str
    dog_tag_number: str | None = None
    id_doc_type: str | None = None
    id_doc_number: str | None = None

    injury_dt: datetime | None = None
    arrival_dt: datetime
    first_aid_before: bool = False
    cause_category: str
    is_combat: bool | None = None

    trauma_types: list[str] = Field(default_factory=list)
    thermal_degree: str | None = None
    wound_types: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    other_text: str | None = None
    diagnosis_text: str
    diagnosis_code: str | None = None
    triage: str | None = None

    flag_urgent: bool = False
    flag_sanitation: bool = False
    flag_isolation: bool = False
    flag_radiation: bool = False

    care_bleeding_control: str | None = None
    care_dressing: str | None = None
    care_immobilization: str | None = None
    care_airway: str | None = None

    care_analgesia_given: bool = False
    care_analgesia_details: str | None = None

    care_antibiotic_given: bool = False
    care_antibiotic_details: str | None = None

    care_antidote_given: bool = False
    care_antidote_details: str | None = None

    care_tetanus: str | None = None
    care_other: str | None = None

    infusion_performed: bool = False
    infusion_volume_ml: int | None = None
    infusion_details: str | None = None

    transfusion_performed: bool = False
    transfusion_volume_ml: int | None = None
    transfusion_details: str | None = None

    sanitation_performed: bool = False
    sanitation_type: str | None = None
    sanitation_details: str | None = None

    evac_destination: str | None = None
    evac_transport: str | None = None
    evac_position: str | None = None
    evac_require_escort: bool | None = None
    evac_oxygen_needed: bool | None = None
    evac_notes: str | None = None

    marks: list[Form100MarkDto] = Field(default_factory=list)
    stages: list[Form100StageCreateRequest] = Field(default_factory=list)


class Form100UpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    birth_date: date | None = None
    rank: str | None = None
    unit: str | None = None
    dog_tag_number: str | None = None
    id_doc_type: str | None = None
    id_doc_number: str | None = None

    injury_dt: datetime | None = None
    arrival_dt: datetime | None = None
    first_aid_before: bool | None = None
    cause_category: str | None = None
    is_combat: bool | None = None

    trauma_types: list[str] | None = None
    thermal_degree: str | None = None
    wound_types: list[str] | None = None
    features: list[str] | None = None
    other_text: str | None = None
    diagnosis_text: str | None = None
    diagnosis_code: str | None = None
    triage: str | None = None

    flag_urgent: bool | None = None
    flag_sanitation: bool | None = None
    flag_isolation: bool | None = None
    flag_radiation: bool | None = None

    care_bleeding_control: str | None = None
    care_dressing: str | None = None
    care_immobilization: str | None = None
    care_airway: str | None = None

    care_analgesia_given: bool | None = None
    care_analgesia_details: str | None = None

    care_antibiotic_given: bool | None = None
    care_antibiotic_details: str | None = None

    care_antidote_given: bool | None = None
    care_antidote_details: str | None = None

    care_tetanus: str | None = None
    care_other: str | None = None

    infusion_performed: bool | None = None
    infusion_volume_ml: int | None = None
    infusion_details: str | None = None

    transfusion_performed: bool | None = None
    transfusion_volume_ml: int | None = None
    transfusion_details: str | None = None

    sanitation_performed: bool | None = None
    sanitation_type: str | None = None
    sanitation_details: str | None = None

    evac_destination: str | None = None
    evac_transport: str | None = None
    evac_position: str | None = None
    evac_require_escort: bool | None = None
    evac_oxygen_needed: bool | None = None
    evac_notes: str | None = None

    marks: list[Form100MarkDto] | None = None


class Form100SignRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    signed_by: str | None = None
    seal_applied: bool = False


class Form100Filters(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str | None = None
    status: Literal["DRAFT", "SIGNED"] | None = None
    unit: str | None = None
    dog_tag_number: str | None = None
    arrival_date_from: date | None = None
    arrival_date_to: date | None = None
    injury_date_from: date | None = None
    injury_date_to: date | None = None


class Form100CardListItemDto(BaseModel):
    id: str
    status: str
    version: int
    last_name: str
    first_name: str
    middle_name: str | None = None
    birth_date: date
    unit: str
    dog_tag_number: str | None = None
    diagnosis_text: str
    created_at: datetime
    updated_at: datetime


class Form100CardDto(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    status: str
    version: int
    qr_payload: str | None = None
    print_number: str | None = None
    corrects_id: str | None = None
    corrected_by_new_id: str | None = None

    last_name: str
    first_name: str
    middle_name: str | None = None
    birth_date: date
    rank: str
    unit: str
    dog_tag_number: str | None = None
    id_doc_type: str | None = None
    id_doc_number: str | None = None

    injury_dt: datetime | None = None
    arrival_dt: datetime
    first_aid_before: bool
    cause_category: str
    is_combat: bool | None = None

    trauma_types: list[str] = Field(default_factory=list)
    thermal_degree: str | None = None
    wound_types: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    other_text: str | None = None
    diagnosis_text: str
    diagnosis_code: str | None = None
    triage: str | None = None

    flag_urgent: bool
    flag_sanitation: bool
    flag_isolation: bool
    flag_radiation: bool

    care_bleeding_control: str | None = None
    care_dressing: str | None = None
    care_immobilization: str | None = None
    care_airway: str | None = None

    care_analgesia_given: bool
    care_analgesia_details: str | None = None
    care_antibiotic_given: bool
    care_antibiotic_details: str | None = None
    care_antidote_given: bool
    care_antidote_details: str | None = None
    care_tetanus: str | None = None
    care_other: str | None = None

    infusion_performed: bool
    infusion_volume_ml: int | None = None
    infusion_details: str | None = None

    transfusion_performed: bool
    transfusion_volume_ml: int | None = None
    transfusion_details: str | None = None

    sanitation_performed: bool
    sanitation_type: str | None = None
    sanitation_details: str | None = None

    evac_destination: str | None = None
    evac_transport: str | None = None
    evac_position: str | None = None
    evac_require_escort: bool | None = None
    evac_oxygen_needed: bool | None = None
    evac_notes: str | None = None

    signed_by: str | None = None
    signed_at: datetime | None = None
    seal_applied: bool

    marks: list[Form100MarkDto] = Field(default_factory=list)
    stages: list[Form100StageDto] = Field(default_factory=list)
