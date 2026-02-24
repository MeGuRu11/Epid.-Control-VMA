from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AnalyticsSearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date_from: date | None = None
    date_to: date | None = None
    department_id: int | None = None
    icd10_code: str | None = None
    microorganism_id: int | None = None
    antibiotic_id: int | None = None
    material_type_id: int | None = None
    growth_flag: int | None = None
    patient_category: str | None = None
    patient_name: str | None = None
    lab_no: str | None = None
    search_text: str | None = None


class AnalyticsSampleRow(BaseModel):
    lab_sample_id: int
    lab_no: str
    patient_name: str
    patient_category: str | None = None
    taken_at: datetime | None = None
    department_name: str | None = None
    material_type: str | None = None
    microorganism: str | None = None
    antibiotic: str | None = None
    growth_flag: int | None = None
