from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

FORM100_STATUS_DRAFT = "DRAFT"
FORM100_STATUS_SIGNED = "SIGNED"


@dataclass(slots=True)
class Form100Mark:
    side: str
    mark_type: str
    shape: dict[str, Any]
    meta: dict[str, Any]
    created_at: datetime | None = None
    created_by: str | None = None


@dataclass(slots=True)
class Form100Stage:
    stage_name: str
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
