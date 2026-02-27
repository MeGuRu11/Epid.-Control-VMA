from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import Patient
from .base import RepoBase


class PatientRepo(RepoBase):
    def list(self) -> list[Patient]:
        with self.tx() as s:
            return list(s.execute(select(Patient).order_by(Patient.created_at.desc())).scalars().all())

    def get(self, patient_id: int) -> Patient | None:
        with self.tx() as s:
            return s.get(Patient, patient_id)

    def create(
        self,
        full_name: str,
        sex: str,
        dob,
        category: str | None = None,
        military_unit: str | None = None,
        military_district: str | None = None,
    ) -> int:
        with self.tx() as s:
            row = Patient(
                full_name=full_name,
                sex=sex,
                dob=dob,
                category=category,
                military_unit=military_unit,
                military_district=military_district,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def update_name(self, patient_id: int, full_name: str) -> bool:
        with self.tx() as s:
            row = s.get(Patient, patient_id)
            if not row:
                return False
            row.full_name = full_name
            return True

    def update_fields(
        self,
        patient_id: int,
        *,
        full_name: str | None = None,
        sex: str | None = None,
        dob=None,
        category: str | None = None,
        military_unit: str | None = None,
        military_district: str | None = None,
    ) -> bool:
        with self.tx() as s:
            row = s.get(Patient, patient_id)
            if not row:
                return False
            if full_name is not None:
                row.full_name = full_name
            if sex is not None:
                row.sex = sex
            if dob is not None:
                row.dob = dob
            if category is not None:
                row.category = category
            if military_unit is not None:
                row.military_unit = military_unit
            if military_district is not None:
                row.military_district = military_district
            return True
