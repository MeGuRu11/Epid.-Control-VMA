from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SanitarySampleCreateIn:
    lab_no: str
    sampling_point: str
    department_id: int | None = None
    room: str | None = None
    growth_flag: int | None = None
    cfu: str | None = None
