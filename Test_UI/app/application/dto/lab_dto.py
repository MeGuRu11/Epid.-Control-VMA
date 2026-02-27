from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabSampleCreateIn:
    patient_id: int
    lab_no: str
    material: str = "Кровь"
    organism: str | None = None
    growth_flag: int | None = None
    mic: str | None = None
    cfu: str | None = None
    emr_case_id: int | None = None

