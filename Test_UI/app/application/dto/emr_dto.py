from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmrCaseCreateIn:
    patient_id: int
    hospital_case_no: str
    department: str | None = None
    department_id: int | None = None


@dataclass(frozen=True)
class EmrVersionIn:
    admission_date: date | None = None
    injury_date: date | None = None
    outcome_date: date | None = None
    outcome_type: str | None = None
    severity: str | None = None
    vph_sp_score: int | None = None
    vph_p_or_score: int | None = None
    sofa_score: int | None = None
    notes: str | None = None
