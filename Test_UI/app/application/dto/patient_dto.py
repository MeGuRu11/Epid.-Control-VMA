from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PatientCreateIn:
    full_name: str
    sex: str = "U"
    dob: date | None = None
    category: str | None = None
    military_unit: str | None = None
    military_district: str | None = None
