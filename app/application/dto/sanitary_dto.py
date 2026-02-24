from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SanitarySampleCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    department_id: int
    sampling_point: str
    room: str | None = None
    medium: str | None = None
    taken_at: datetime | None = None
    delivered_at: datetime | None = None
    created_by: int | None = None


class SanitarySampleResultUpdate(BaseModel):
    growth_result_at: datetime | None = None
    growth_flag: int | None = Field(default=None)
    colony_desc: str | None = None
    microscopy: str | None = None
    cfu: str | None = None
    microorganism_id: int | None = None
    microorganism_free: str | None = None
    susceptibility: list[dict] = Field(default_factory=list)
    phages: list[dict] = Field(default_factory=list)


class SanitarySampleUpdateRequest(BaseModel):
    sampling_point: str | None = None
    room: str | None = None
    medium: str | None = None
    taken_at: datetime | None = None
    delivered_at: datetime | None = None


class SanitarySampleResponse(BaseModel):
    id: int
    lab_no: str
    department_id: int
    sampling_point: str | None = None
    room: str | None = None
    medium: str | None = None
    taken_at: datetime | None
    growth_flag: int | None
    microorganism_id: int | None = None
    microorganism_free: str | None = None
