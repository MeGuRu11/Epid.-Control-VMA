from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.constants import MilitaryCategory


class PatientCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(..., min_length=1)
    dob: date | None = None
    sex: str = Field(default="U", pattern="^(M|F|U)$")
    category: str = Field(..., min_length=1)
    military_unit: str | None = None
    military_district: str | None = None

    @classmethod
    @field_validator("category")
    def _validate_category(cls, v: str) -> str:
        if v not in MilitaryCategory.values():
            raise ValueError("Категория должна быть из списка")
        return v


class PatientResponse(BaseModel):
    id: int
    full_name: str
    dob: date | None = None
    sex: str
    category: str | None = None
    military_unit: str | None = None
    military_district: str | None = None
