from __future__ import annotations

from datetime import date

from ...application.dto.patient_dto import PatientCreateIn
from ...domain.rules import normalize_required_text
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.patient_repo import PatientRepo


class PatientService:
    def __init__(self, engine, session_ctx):
        self._session = session_ctx
        self._audit = AuditLogger(engine)
        self._repo = PatientRepo(engine)

    def list(self, q: str = ""):
        rows = self._repo.list()
        query = (q or "").strip().lower()
        if not query:
            return rows
        return [p for p in rows if query in (p.full_name or "").lower() or query == str(p.id)]

    def details(self, patient_id: int):
        return self._repo.get(patient_id)

    def create(
        self,
        full_name: str,
        sex: str = "U",
        dob: date | None = None,
        category: str | None = None,
        military_unit: str | None = None,
        military_district: str | None = None,
    ) -> int:
        dto = PatientCreateIn(
            full_name=normalize_required_text(full_name),
            sex=sex or "U",
            dob=dob,
            category=category,
            military_unit=military_unit,
            military_district=military_district,
        )
        patient_id = self._repo.create(
            full_name=dto.full_name,
            sex=dto.sex,
            dob=dto.dob,
            category=dto.category,
            military_unit=dto.military_unit,
            military_district=dto.military_district,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "patients",
                str(patient_id),
                "create",
                {"full_name": dto.full_name, "sex": dto.sex},
            )
        )
        return patient_id

    def rename(self, patient_id: int, full_name: str) -> bool:
        ok = self._repo.update_name(patient_id, full_name.strip())
        if ok:
            self._audit.log(
                AuditEvent(
                    self._session.user_id,
                    self._session.login,
                    "patients",
                    str(patient_id),
                    "rename",
                    {"full_name": full_name},
                )
            )
        return ok

    def update_details(
        self,
        patient_id: int,
        *,
        full_name: str | None = None,
        sex: str | None = None,
        dob: date | None = None,
        category: str | None = None,
        military_unit: str | None = None,
        military_district: str | None = None,
    ) -> bool:
        ok = self._repo.update_fields(
            patient_id,
            full_name=full_name.strip() if full_name else None,
            sex=sex,
            dob=dob,
            category=category,
            military_unit=military_unit,
            military_district=military_district,
        )
        if ok:
            self._audit.log(
                AuditEvent(
                    self._session.user_id,
                    self._session.login,
                    "patients",
                    str(patient_id),
                    "update_details",
                    {
                        "full_name": full_name,
                        "sex": sex,
                        "category": category,
                        "military_unit": military_unit,
                        "military_district": military_district,
                    },
                )
            )
        return ok
